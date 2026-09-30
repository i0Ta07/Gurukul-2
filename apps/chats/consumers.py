from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string
from apps.classes.models import ClassMembership
from apps.chats.models import ChatThread, RoomMessage,ChatRoom, ThreadMessage
import json
from asgiref.sync import sync_to_async
from django.utils.dateformat import format
from django.utils import timezone

class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.classroom_id = self.scope["url_route"]["kwargs"]["classroom_id"]
        self.user = self.scope["user"]
        self.room_group_name = None

        if self.user.is_anonymous:
            await self.close(code=4001)
            return

        try:
            self.room = await ChatRoom.objects.select_related('classroom').aget(pk = self.classroom_id)
        except ChatRoom.DoesNotExist:
            await self.close(4004)
            return

        is_member = await ClassMembership.objects.filter(classroom_id=self.classroom_id, user_id=self.user.id).aexists()

        if not is_member:
            is_owner = (self.room.classroom.owner.id == self.user.id)

            if not is_owner:
                await self.close(code=4003)
                return

        self.room_group_name = f"room_{self.classroom_id}"

        # Add the channel to the group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            body = text_data_json["body"]
        except (json.JSONDecodeError, KeyError):
            await self.send(text_data=json.dumps({
                "error": "Invalid message format."
            }))
            return

        body = body.strip()

        if not body:
            return
        message = await RoomMessage.objects.acreate(body = body,author = self.user,room = self.room)
        await self.room.asave(update_fields=["updated_at"])

        room_context = { 
            "message": {'id':message.id,'body':message.body,'created_at':format(timezone.localtime(message.created_at),"j M, Y, g:i A"),'is_edited':message.is_edited,'is_editable':True,'author':{'id':message.author_id,'get_full_name':message.author.get_full_name(),'username':message.author.username,}},
            'message_type':"room"
            }
        if message.author.profile_photo:
            room_context['message']['author']['profile_photo'] = {'url':message.author.profile_photo.url}
        # Send message to room group
        await self.channel_layer.group_send(
            # cannot send the message django instance, only JSON-serializable
            self.room_group_name, {"type": "room.message", "context": room_context
            }
        )

    # Receive message from room group
    async def room_message(self, event):
        context = event["context"]
        html = await sync_to_async(render_to_string)(
            "chats/partials/ws_room_message.html",
            context={**context,'current_user_id':self.user.id}
        )
        # Send message to each WebSocket connection in the group. 
        await self.send(text_data=html)

    async def edit_message(self,event):
        context = event['context']
        html = await sync_to_async(render_to_string)(
            "chats/partials/ws_edit_room_message.html",
            context={**context,'current_user_id':self.user.id,'id':context['message']['id']}
        )
        await self.send(text_data=html)   
    
    async def disconnect(self, close_code):
        # Leave room group. Add logging with code.
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name) 
        
class ThreadConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user1_id = self.scope["url_route"]["kwargs"]["user1_id"]
        self.user2_id = self.scope["url_route"]["kwargs"]["user2_id"]
        self.user = self.scope["user"]
        self.room_group_name = None

        if self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.thread,_ = await sync_to_async(ChatThread.get_or_create_thread)(sender_id=self.user1_id,receiver_id=self.user2_id)

        self.other_user = self.thread.user2 if self.user == self.thread.user1 else self.thread.user1
        self.room_group_name = f"thread_{self.thread.id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            body = text_data_json["body"]
        except (json.JSONDecodeError, KeyError):
            await self.send(text_data=json.dumps({
                "error": "Invalid message format."
            }))
            return

        body = body.strip()

        if not body:
            return
        message = await ThreadMessage.objects.acreate(body = body,author = self.user,thread = self.thread)
        await self.thread.asave(update_fields=["updated_at"])

        await self.channel_layer.group_send(
            self.room_group_name, {"type": "thread.message", 
            "context": {
                "message": {'id':message.id,'body':message.body,'created_at':format(timezone.localtime(message.created_at),"j M, Y, g:i A"),'is_edited':message.is_edited,'is_editable':True,'author':{'id':message.author_id}},
                'message_type':"thread"
                }
            }
        )

    # Other user is webscoket specific connection data that is changed as per the websocket but the message is a shared entity.
    #  Hence we don't render the message inside recieve but rather leave it specific to each connection.
    async def thread_message(self, event):
        context = event["context"]

        html = await sync_to_async(render_to_string)(
            "chats/partials/ws_thread_message.html",
            context= {**context,'other_user':self.other_user}
        )
        await self.send(text_data=html)

    async def edit_message(self,event):
        context = event['context']
        html = await sync_to_async(render_to_string)(
            "chats/partials/ws_edit_thread_message.html",
            context={**context,'other_user':self.other_user,'id':context['message']['id']}
        )
        await self.send(text_data=html)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name) 
    