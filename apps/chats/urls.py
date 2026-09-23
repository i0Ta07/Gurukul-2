from django.urls import path
from apps.chats.views import ChatHome,ChatUsers,ChatRooms,LoadThreadMessages,LoadRoomMessages,SendRoomMessages,SendThreadMessage

urlpatterns = [

    path("home/", ChatHome.as_view(), name="chat-home"),
    path("users/", ChatUsers.as_view(), name="chat-users"),
    path("rooms/", ChatRooms.as_view(), name="chat-rooms"),
    path("thread/<int:thread_id>",LoadThreadMessages.as_view(), name="thread"),
    path("room/<int:classroom_id>",LoadRoomMessages.as_view(), name="room"),
    path("thread/send/<int:thread_id>/",SendThreadMessage.as_view(),name="send-thread-message"),
    path("room/send/<int:classroom_id>/",SendRoomMessages.as_view(),name="send-room-message"),

]