from django.urls import path

from apps.chats.consumers import RoomConsumer

chat_websocket_urlpatterns = [
    path("rooms/<int:classroom_id>/", RoomConsumer.as_asgi()),
    # path("ws/chats/threads/<int:thread_id>",)
]