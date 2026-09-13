from django.contrib import admin
from apps.chats.models import Message,RoomMessage,ChatRoom,ChatThread

# Register your models here.

admin.site.register(Message)
admin.site.register(RoomMessage)
admin.site.register(ChatRoom)
admin.site.register(ChatThread)
