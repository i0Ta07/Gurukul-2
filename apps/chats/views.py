from django.shortcuts import render,get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.chats.models import ChatThread,ChatRoom,ThreadMessage,RoomMessage
from django.db.models import Q, OuterRef,Subquery
from apps.chats.forms import ThreadMessageForm,RoomMessageForm
from apps.classes.mixins import ClassroomMembershipRequired
from apps.classes.models import ClassMembership
from config.utils import create_message_and_redirect
# Create your views here.

class ChatHome(LoginRequiredMixin,View):
    def get(self,request, *args, **kwargs):
        if request.htmx:
            return render(request,"chats/chat_home.html#chat-home")
        return render(request,"chats/chat_home.html")

class ChatUsers(LoginRequiredMixin, View):
    THREAD_LAST_MESSAGE_SIZE = 75
    OTHER_USER_DISPLAY_NAME_SIZE = 40

    def get(self, request, *args, **kwargs):
        current_user = request.user

        # Subquery to pick the most recent ThreadMessage for each thread
        latest_thread_msg = ThreadMessage.objects.filter(thread_id=OuterRef('pk')).order_by('-created_at')

        threads = (
            ChatThread.objects.filter(
                Q(user1=current_user) | Q(user2=current_user)
            )
            .select_related('user1', 'user2')  # Prevents extra queries when accessing user details
            .annotate(
                last_message_body=Subquery(latest_thread_msg.values('body')[:1]),
                last_message_time=Subquery(latest_thread_msg.values('created_at')[:1]),
                last_message_author_id = Subquery(latest_thread_msg.values('author_id')[:1])
            )
            .order_by('-updated_at')[:30]
        )
        for thread in threads:
            thread.other_user = thread.user2 if request.user == thread.user1 else thread.user1

            other_user_name = thread.other_user.get_full_name()
            if len(other_user_name) > self.OTHER_USER_DISPLAY_NAME_SIZE:
                other_user_name = other_user_name[:self.OTHER_USER_DISPLAY_NAME_SIZE] + '...'
            thread.other_user_name = other_user_name


            if thread.last_message_author_id != thread.other_user.id:
                thread.last_message_body = 'You: ' + thread.last_message_body
            if len(thread.last_message_body)> self.THREAD_LAST_MESSAGE_SIZE:
                thread.last_message_body = thread.last_message_body[:self.THREAD_LAST_MESSAGE_SIZE] + '...'


        context = {'threads': threads}
        return render(request, "chats/partials/threads.html", context)

class ChatRooms(LoginRequiredMixin, View):
    GROUP_LAST_MESSAGE_SIZE = 80
    CLASSRROM_DISPLAY_NAME_SIZE = 45

    def get(self, request, *args, **kwargs):
        # Subquery to pick the most recent RoomMessage for each room
        latest_room_msg = RoomMessage.objects.filter(
            room=OuterRef('pk')
        ).order_by('-created_at')

        rooms = (
            ChatRoom.objects.filter(
                classroom__membership__user=request.user,
                classroom__membership__status='A'
            )
            .select_related('classroom')
            .annotate(
                last_message_body=Subquery(latest_room_msg.values('body')[:1]),
                last_message_time=Subquery(latest_room_msg.values('created_at')[:1]),
                last_message_author_id=Subquery(latest_room_msg.values('author__id')[:1]),
                last_message_author_first_name=Subquery(latest_room_msg.values('author__first_name')[:1]),
                last_message_author_last_name=Subquery(latest_room_msg.values('author__last_name')[:1]),
            )
            .distinct()
        )

        for room in rooms: 
            if len(room.classroom.name) > self.CLASSRROM_DISPLAY_NAME_SIZE:
                room.classroom.name = room.classroom.name[:self.CLASSRROM_DISPLAY_NAME_SIZE] + '...'
            if room.last_message_author_id == request.user.id:
                room.message_body = 'You: ' + room.last_message_body
            else:
                room.message_body = room.last_message_author_first_name + ' ' +  room.last_message_author_last_name + ': ' + room.last_message_body
            if len(room.message_body) > self.GROUP_LAST_MESSAGE_SIZE:
                room.message_body = room.message_body[:self.GROUP_LAST_MESSAGE_SIZE] + '...'
        context = {"rooms": rooms} 
        return render(request, "chats/partials/rooms.html", context)

class LoadThreadMessages(LoginRequiredMixin,View):
    form_class = ThreadMessageForm

    def get(self,request,*args,**kwargs):
        thread_id = kwargs.get("thread_id")
        thread = get_object_or_404(ChatThread,pk = thread_id)
        messages = ThreadMessage.objects.filter(thread = thread).select_related("author").order_by('created_at')[:50]
        other_user = thread.user1 if request.user.id == thread.user2.id else thread.user2
        form = self.form_class()
        context = {"messages":messages,"other_user":other_user,'form':form, 'thread_id':thread_id}
        return render(request,"chats/partials/thread_messages.html",context)

class LoadRoomMessages(LoginRequiredMixin,ClassroomMembershipRequired,View):
    form_class = RoomMessageForm
    def get(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        messages = RoomMessage.objects.filter(room_id = classroom.id).select_related("author").order_by("created_at")[:50]
        form = self.form_class()
        context = {"messages":messages,"room_name":classroom.name,'form':form,'classroom_id':classroom.id}
        return render(request,"chats/partials/room_messages.html",context)

class SendRoomMessages(LoginRequiredMixin,ClassroomMembershipRequired,View):
    form_class = RoomMessageForm
    def post(self,request, *args, **kwargs):
        form = self.form_class(request.POST)
        if not form.is_valid():
            return create_message_and_redirect(request=request,message="Some error occured",url="users-dashboard",code="error")
        
        classroom = self.get_classroom()
        membership_exists = ClassMembership.objects.filter(user=request.user, classroom=classroom).exists()
        if not membership_exists and request.user != self.room.classroom.owner: 
            return create_message_and_redirect(request=request,message="You are NOT part of this room.",url="users-dashboard",code="warning")
        room_message = form.save(commit=False)
        room_message.author = request.user
        room_message.room = classroom.chatroom
        room_message.save()
        return render(request,"chats/partials/room_messages.html#send-room-message",{'message':room_message})

class SendThreadMessage(LoginRequiredMixin,View):
    form_class= ThreadMessageForm
    def post(self,request, *args, **kwargs):
        form = self.form_class(request.POST)
        if not form.is_valid():
            return create_message_and_redirect(request=request,message="Some error occured",url="users-dashboard",code="error")
        
        thread_id = kwargs.get("thread_id")
        thread = get_object_or_404(ChatThread,pk = thread_id)
        if thread.user1.id != request.user.id and thread.user2.id != request.user.id:
            return  create_message_and_redirect(request=request,message="You are NOT part of this thread",url="users-dashboard",code="warning")
        thread_message = form.save(commit=False)
        thread_message.thread = thread
        thread_message.author = request.user
        thread_message.save()
        return render(request,"chats/partials/thread_messages.html#send-thread-message",{'message':thread_message})

