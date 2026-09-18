from django.urls import path
from apps.chats.views import ChatHome,ChatUsers,ChatRooms,LoadThreadMessages,LoadRoomMessages

urlpatterns = [

    path("home/", ChatHome.as_view(), name="chat-home"),
    path("users/", ChatUsers.as_view(), name="chat-users"),
    path("rooms/", ChatRooms.as_view(), name="chat-rooms"),
    path("thread/<int:thread_id>",LoadThreadMessages.as_view(), name="thread"),
    path("room/<int:room_id>",LoadRoomMessages.as_view(), name="room")
]