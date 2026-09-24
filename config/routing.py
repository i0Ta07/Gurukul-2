from django.urls import path
from channels.routing import URLRouter
from apps.chats.routing import chat_websocket_urlpatterns

websocket_urlpatterns = [
    path("ws/chats/", URLRouter(chat_websocket_urlpatterns)),
]