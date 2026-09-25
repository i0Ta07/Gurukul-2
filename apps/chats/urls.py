from django.urls import path
from apps.chats.views import ChatHome,ListUsers,ListRooms,LoadThreadMessages,LoadRoomMessages

urlpatterns = [

    path("home/", ChatHome.as_view(), name="chat-home"),
    path("users/", ListUsers.as_view(), name="chat-users"),
    path("rooms/", ListRooms.as_view(), name="chat-rooms"),
    path("thread/<int:thread_id>",LoadThreadMessages.as_view(), name="thread"),
    path("room/<int:classroom_id>",LoadRoomMessages.as_view(), name="room"),

]