from django.urls import path
from apps.chats.views import ChatHome,ListUsers,ListRooms,LoadThreadMessages,LoadRoomMessages,SearchUsers,EditMessage,DeleteMessage

urlpatterns = [

    path("home/", ChatHome.as_view(), name="chat-home"),
    path("users/", ListUsers.as_view(), name="chat-users"),
    path("rooms/", ListRooms.as_view(), name="chat-rooms"),
    path("room/<int:classroom_id>",LoadRoomMessages.as_view(), name="room"),
    path("thread/<int:thread_id>",LoadThreadMessages.as_view(), name="thread"),
    path("search/users/",SearchUsers.as_view(), name="search-users"),
    path("load/thread/<int:other_user_id>/",LoadThreadMessages.as_view(), name="search-chat"),
    path("edit/thread/message/<int:thread_message_id>/",EditMessage.as_view(), name="edit-thread-message"),
    path("edit/room/message/<int:room_message_id>/",EditMessage.as_view(), name="edit-room-message"),
    path("delete/thread/message/<int:thread_message_id>/",DeleteMessage.as_view(), name="delete-thread-message"),
    path("delete/room/message/<int:room_message_id>/",DeleteMessage.as_view(), name="delete-room-message"),

]