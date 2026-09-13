from django.urls import path
from apps.chats.views import ChatHome,ChatUsers,ChatRooms

urlpatterns = [

    path("home/", ChatHome.as_view(), name="chat-home"),
    path("users/", ChatUsers.as_view(), name="chat-users"),
    path("rooms/", ChatRooms.as_view(), name="chat-rooms"),
]