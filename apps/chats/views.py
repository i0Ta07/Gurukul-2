from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

# Create your views here.

class ChatHome(LoginRequiredMixin,View):
    def get(self,request, *args, **kwargs):
        if request.htmx:
            return render(request,"chats/chat_home.html#chat-home")
        return render(request,"chats/chat_home.html")

class ChatUsers(LoginRequiredMixin,View):
    def get(self,request, *args, **kwargs):
        return render(request,"chats/partials/chat_window.html#chat-window")


class ChatRooms(LoginRequiredMixin,View):
    def get(self,request, *args, **kwargs):
        return render(request,"chats/partials/chat_window.html#chat-window")

