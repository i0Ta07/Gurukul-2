from django.urls import path

from apps.chats.consumers import RoomConsumer,ThreadConsumer

chat_websocket_urlpatterns = [
    path("rooms/<int:classroom_id>/", RoomConsumer.as_asgi()),
    path("threads/<int:thread_id>/",ThreadConsumer.as_asgi()),
]