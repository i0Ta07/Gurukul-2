from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string
from apps.classes.models import ClassMembership
from apps.chats.models import ChatThread, RoomMessage,ChatRoom, ThreadMessage
import json
from asgiref.sync import sync_to_async
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

        # Send message to room group
        await self.channel_layer.group_send(
            # cannot send the message django instance, only JSON-serializable
            self.room_group_name, {"type": "room.message", "message_id": message.id}
        )

    # Receive message from room group
    async def room_message(self, event):
        message_id = event["message_id"]
        try:
            message = await RoomMessage.objects.aget(pk= message_id)
        except RoomMessage.DoesNotExist:
            await self.close(4004)
            return
        
        html = await sync_to_async(render_to_string)(
            "chats/partials/ws_room_message.html",
            context={"message": message,'current_user_id':self.user.id}
        )
        # Send message to each WebSocket connection in the group. 
        await self.send(text_data=html)

    async def disconnect(self, close_code):
        # Update user's last_seen
        self.user.last_seen = timezone.now()
        await self.user.asave(update_fields=["last_seen"])
        # Leave room group. Add logging with code.
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name) 
        
class ThreadConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.thread_id = self.scope["url_route"]["kwargs"]["thread_id"]
        self.user = self.scope["user"]
        self.room_group_name = None

        if self.user.is_anonymous:
            await self.close(code=4001)
            return

        try:
            self.thread = await ChatThread.objects.select_related('user1','user2').aget(pk = self.thread_id)
        except ChatThread.DoesNotExist:
            await self.close(4004)
            return
        
        belong_to_thread = (self.user.id != self.thread.user1 and self.user.id != self.thread.user2)

        if not belong_to_thread:
            await self.close(code=4003)
            return

        self.other_user = self.thread.user2 if self.user == self.thread.user1 else self.thread.user1
        self.room_group_name = f"thread_{self.thread_id}"

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
            self.room_group_name, {"type": "thread.message", "message_id": message.id}
        )

    async def thread_message(self, event):
        message_id = event["message_id"]
        try:
            message = await ThreadMessage.objects.aget(pk= message_id)
        except ThreadMessage.DoesNotExist:
            await self.close(4004)
            return

        html = await sync_to_async(render_to_string)(
            "chats/partials/ws_thread_message.html",
            context={"message": message,'other_user':self.other_user}
        )
        await self.send(text_data=html)

    async def disconnect(self, close_code):
        self.user.last_seen = timezone.now()
        await self.user.asave(update_fields=["last_seen"])
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name) 
    