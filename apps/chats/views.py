from channels.layers import get_channel_layer
from django.http import HttpResponse
from django.shortcuts import render,get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.chats.models import ChatThread,ChatRoom,ThreadMessage,RoomMessage
from django.db.models import Q, OuterRef,Subquery,Case, When, Value, BooleanField
from apps.chats.forms import ThreadMessageForm,RoomMessageForm, SearchUserForm
from apps.classes.mixins import ClassroomMembershipRequired
from django.core.cache import cache
from apps.users.models import User
from apps.users.utils import get_user_online_key
from asgiref.sync import async_to_sync
from django.utils.dateformat import format
from django.utils import timezone
from datetime import timedelta
# Create your views here.

class ChatHome(LoginRequiredMixin,View):
    def get(self,request, *args, **kwargs):
        if request.htmx:
            return render(request,"chats/chat_home.html#chat-home")
        return render(request,"chats/chat_home.html")

class ListUsers(LoginRequiredMixin, View):
    THREAD_LAST_MESSAGE_SIZE = 75
    OTHER_USER_DISPLAY_NAME_SIZE = 40
    form_class = SearchUserForm

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
            .order_by('-updated_at')[:25]
        )
        for thread in threads:
            thread.other_user = thread.user2 if request.user == thread.user1 else thread.user1

            other_user_name = thread.other_user.get_full_name()
            if len(other_user_name) > self.OTHER_USER_DISPLAY_NAME_SIZE:
                other_user_name = other_user_name[:self.OTHER_USER_DISPLAY_NAME_SIZE] + '...'
            thread.other_user_name = other_user_name

            if thread.last_message_body:
                if thread.last_message_author_id != thread.other_user.id:
                    thread.last_message_body = 'You: ' + thread.last_message_body
                if len(thread.last_message_body)> self.THREAD_LAST_MESSAGE_SIZE:
                    thread.last_message_body = thread.last_message_body[:self.THREAD_LAST_MESSAGE_SIZE] + '...'
        
        context = {'threads': threads,'form':self.form_class()}
        return render(request, "chats/partials/threads.html", context)

class ListRooms(LoginRequiredMixin, View):
    GROUP_LAST_MESSAGE_SIZE = 80
    CLASSRROM_DISPLAY_NAME_SIZE = 45

    def get(self, request, *args, **kwargs):
        # Subquery to pick the most recent RoomMessage for each room
        latest_room_msg = RoomMessage.objects.filter(
            room=OuterRef('pk')
        ).order_by('-created_at')

        rooms = (
            ChatRoom.objects.filter(
                Q(classroom__membership__user=request.user,classroom__membership__status='A') | Q(classroom__owner = request.user))
            .select_related('classroom')
            .annotate(
                last_message_body=Subquery(latest_room_msg.values('body')[:1]),
                last_message_time=Subquery(latest_room_msg.values('created_at')[:1]),
                last_message_author_id=Subquery(latest_room_msg.values('author__id')[:1]),
                last_message_author_first_name=Subquery(latest_room_msg.values('author__first_name')[:1]),
                last_message_author_last_name=Subquery(latest_room_msg.values('author__last_name')[:1]),
            )
            .order_by('-updated_at').distinct()[:25]
        )

        for room in rooms: 
            if len(room.classroom.name) > self.CLASSRROM_DISPLAY_NAME_SIZE:
                room.classroom.name = room.classroom.name[:self.CLASSRROM_DISPLAY_NAME_SIZE] + '...'

            if room.last_message_body:
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
        other_user_id = kwargs.get("other_user_id")
        created = False
        if thread_id:
            thread = get_object_or_404(ChatThread.objects.select_related('user1','user2'),pk = thread_id)
            other_user = thread.user1 if request.user.id == thread.user2.id else thread.user2
        elif other_user_id:
            other_user = get_object_or_404(User,pk = other_user_id)
            thread,created = ChatThread.get_or_create_thread(sender_id=request.user.id,receiver_id=other_user_id)
        form = self.form_class()
        key = get_user_online_key(user_id=other_user.id)
        other_user_is_online = cache.get(key,False)
        context = {"other_user":other_user,'form':form, 'thread_id':thread_id,'is_online':other_user_is_online}
        if not created:
            messages = (
                ThreadMessage.objects.filter(thread=thread).select_related("author")
                .annotate(
                    is_editable=Case(
                        When(
                            created_at__gte=timezone.now() - timedelta(minutes=15),
                            then=Value(True),
                        ),
                        default=Value(False),
                        output_field=BooleanField(),
                    )
                )
                .order_by("created_at")
            )
            context['messages'] = messages

        return render(request,"chats/partials/thread_messages.html",context)

class LoadRoomMessages(LoginRequiredMixin,ClassroomMembershipRequired,View):
    form_class = RoomMessageForm
    def get(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        messages = (
            RoomMessage.objects.filter(room_id=classroom.id).select_related("author")
            .annotate(
                is_editable=Case(
                    When(
                        created_at__gte=timezone.now() - timedelta(minutes=15),
                        then=Value(True),
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            )
            .order_by("created_at")
        )
        form = self.form_class()
        context = {"messages":messages,"room_name":classroom.name,'form':form,'classroom_id':classroom.id,'current_user_id':request.user.id}
        return render(request,"chats/partials/room_messages.html",context)

class SearchUsers(LoginRequiredMixin,View):
    form_class = SearchUserForm
    template_name = 'chats/partials/search_users.html'

    def post(self,request,*args,**kwargs):
        form = self.form_class(request.POST)
        if not form.is_valid():
            return render(request,self.template_name,{'form':form})
        username = form.cleaned_data['username']
        users = User.objects.filter(username__istartswith=username).exclude(pk=request.user.pk)
        return render(request,self.template_name,{'users':users,'form':self.form_class()})

class EditMessage(LoginRequiredMixin,View):
    thread_form_class = ThreadMessageForm
    room_form_class = RoomMessageForm
    template_name = "chats/partials/edit_message.html"
    def get(self,request,*args,**kwargs):
        thread_message_id = kwargs.get('thread_message_id')
        if thread_message_id:
            message =  get_object_or_404(ThreadMessage.objects.select_related('author'),pk= thread_message_id)
        if not thread_message_id:
            room_message_id = kwargs.get('room_message_id')
            message = get_object_or_404(RoomMessage.objects.select_related('author'),pk = room_message_id)

        if not message.created_at >= timezone.now() - timedelta(minutes=15):
            return HttpResponse(
                "<p class='text-center'>You can only edit a message before 15 minutes.<p>",status=200,)
        
        if message.author.id != request.user.id:
            return HttpResponse(
                "<p class='text-center'>You are not the author of this message, hence you cannot edit it. Do not mess with US.<p>",status=200,)

        form = self.thread_form_class(initial={'body':message.body})
        if not thread_message_id:
            form = self.room_form_class(initial={'body':message.body})

        return render(request,self.template_name,{'form':form,**kwargs})
    
    def post(self,request,*args,**kwargs):
        thread_message_id = kwargs.get('thread_message_id')
        if thread_message_id:
            message = get_object_or_404(ThreadMessage.objects.select_related('author','thread'),pk=thread_message_id)
        
        if not thread_message_id:
            room_message_id = kwargs.get('room_message_id')
            message = get_object_or_404(RoomMessage.objects.select_related('author','room__classroom'),pk=room_message_id)

        if not message.created_at >= timezone.now() - timedelta(minutes=15):
            return HttpResponse(
                "<p class='text-center'>You can only edit a message before 15 minutes.<p>",status=200,)
        
        if message.author.id != request.user.id:
            return HttpResponse(
                "<p class='text-center'>You are not the author of this message, hence you cannot edit it. Do not mess with US.<p>",
                status=200,)

        form = self.thread_form_class(request.POST)
        if not thread_message_id:
            form = self.room_form_class(request.POST)
        if not form.is_valid():
            return render(request,self.template_name,{'form':form,**kwargs})
        
        new_body = form.cleaned_data['body']
        message.body = new_body
        message.is_edited = True
        message.save(update_fields=['body','is_edited']) 

        if thread_message_id:
            room_group_name = f"thread_{message.thread.id}"
            payload = {'type':'edit.message',
                "context": {
                    "message": {'id':message.id,'body':message.body,'created_at':format(timezone.localtime(message.created_at),"j M, Y, g:i A"),'is_edited':message.is_edited,'is_editable':True,'author':{'id':message.author_id}},
                },
            }
        else:
            room_group_name = f"room_{message.room.classroom.id}"
            payload = {"type": "edit.message",
                "context": { 
                        "message": {'id':message.id,'body':message.body,'created_at':format(timezone.localtime(message.created_at),"j M, Y, g:i A"),'is_edited':message.is_edited, 'is_editable':True,'author':{'id':message.author_id,'get_full_name':message.author.get_full_name(),'username':message.author.username,'profile_photo':{'url':message.author.profile_photo.url}}},
                },
            }
            
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            payload 
        )
        response  = HttpResponse("",status= 200)
        response['HX-Trigger'] = 'message-edited'
        return response