from django.db import models
from apps.classes.models import Classroom
from apps.users.models import User
from django.db.models import Q, F

class ChatRoom(models.Model):
    classroom = models.OneToOneField(
        Classroom,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="chatroom",
    )

    def __str__(self):
        return f"{self.classroom.name} ({self.classroom.id})'s Room"

class Message(models.Model):
    body = models.CharField(max_length=300)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="messages",
        related_query_name="message"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.id}"

class RoomMessage(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        models.CASCADE,
        related_name="messages",
        related_query_name="message"
    )
    body = models.CharField(max_length=300)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="room_messages",
        related_query_name="room_message"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.room.id}, {self.author.id}"

class ChatThread(models.Model):
    user1 = models.ForeignKey(
        User,
        models.CASCADE,
        related_name="threads_user1",
        related_query_name="thread_user1"
    )
    user2 = models.ForeignKey(
        User,
        models.CASCADE,
        related_name="threads_user2",
        related_query_name="thread_user2"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['-updated_at'],name="thread_last_updated_at_index"), 
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user1', 'user2'], 
                name='unique_users_thread'
            ),
            models.CheckConstraint(
                condition=Q(user1__gte = F('user2')),
                name= "user1_lte_user2"
            )
        ]

    def __str__(self):
        return f"{self.user1.id},{self.user2.id}" 

    @classmethod
    def get_or_create_thread(cls, u1, u2): # Thread.get_or_create_thread
        # Always order the users so the smaller ID is user1
        user1, user2 = (u1, u2) if u1.pk < u2.pk else (u2, u1)
        thread, created = cls.objects.get_or_create(user1=user1, user2=user2)
        return thread # thread.save() to trigger auto_add during websocket disconnection.