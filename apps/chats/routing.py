from django.urls import path

from apps.chats.consumers import RoomConsumer,ThreadConsumer

chat_websocket_urlpatterns = [
    path("rooms/<int:classroom_id>/", RoomConsumer.as_asgi()),
    path("users/<int:user1_id>/<int:user2_id>/",ThreadConsumer.as_asgi()),
]