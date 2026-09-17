from django.contrib import admin
from apps.chats.models import ThreadMessage,RoomMessage,ChatRoom,ChatThread

# Register your models here.

admin.site.register(ThreadMessage)
admin.site.register(RoomMessage)
admin.site.register(ChatRoom)
admin.site.register(ChatThread)
