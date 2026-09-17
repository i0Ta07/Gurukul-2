from django.shortcuts import get_object_or_404, render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.classes.models import ClassMembership,Classroom
from apps.chats.models import ChatThread,ChatRoom,ThreadMessage,RoomMessage
from django.db.models import Q, OuterRef,Subquery
# Create your views here.

class ChatHome(LoginRequiredMixin,View):
    def get(self,request, *args, **kwargs):
        if request.htmx:
            return render(request,"chats/chat_home.html#chat-home")
        return render(request,"chats/chat_home.html")

class ChatUsers(LoginRequiredMixin, View):
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
            if len(other_user_name) > 15:
                other_user_name = other_user_name[:15] + '...'
            thread.other_user_name = other_user_name


            if thread.last_message_author_id != thread.other_user.id:
                thread.last_message_body = 'You: ' + thread.last_message_body
            if len(thread.last_message_body)> 45:
                thread.last_message_body = thread.last_message_body[:45] + '...'


        context = {'threads': threads}
        return render(request, "chats/partials/threads.html", context)

class ChatRooms(LoginRequiredMixin, View):
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
                last_message_author_first_name=Subquery(latest_room_msg.values('author__first_name')[:1]),
                last_message_author_last_name=Subquery(latest_room_msg.values('author__last_name')[:1]),
            )
            .distinct()
        )

        for room in rooms: 
            if len(room.classroom.name) > 25:
                room.classroom.name = room.classroom.name[:25] + '...'
            room.message_body = room.last_message_author_first_name + ' ' +  room.last_message_author_last_name + ': ' + room.last_message_body
            if len(room.message_body) > 45:
                room.message_body = room.message_body[:45]
        context = {"rooms": rooms} 
        return render(request, "chats/partials/rooms.html", context)

class LoadThreadMessages(LoginRequiredMixin,View):
    def get(self,request,*args,**kwargs):
        thread_id = kwargs.get("thread_id")
        thread = get_object_or_404(ChatThread,pk = thread_id)
        messages = ThreadMessage.objects.filter(thread = thread)
        other_user = thread.user1 if request.user.id == thread.user2.id else thread.user2.id
        context = {"messages":messages,"other_user":other_user}
        return render(request,"chats/partials/thread_messages.html",context)

        
