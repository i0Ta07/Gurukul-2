from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string
from apps.classes.models import ClassMembership
from apps.chats.models import RoomMessage,ChatRoom
import json
from asgiref.sync import sync_to_async

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
            self.room_group_name, {"type": "chat.message", "message_id": message.id}
        )

    # Receive message from room group
    async def chat_message(self, event):
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
        # Leave room group. Add logging with code.
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name) 
        
