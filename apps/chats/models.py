from django.db import models
from apps.classes.models import ClassMembership, Classroom
from apps.users.models import User
from django.db.models import Q, F
from django.core.exceptions import ValidationError

class ChatRoom(models.Model):
    classroom = models.OneToOneField(
        Classroom,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="chatroom",
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.classroom.name} ({self.classroom.id})'s Room"
    
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
        return f"{self.room.classroom.name} ({self.author.get_full_name()})"

    class Meta:
        ordering = ['-created_at']

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
    # Add last scene of each user so we can determine which message is new.

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
        return f"{self.user1.get_full_name()}, {self.user2.get_full_name()}"

    def clean(self):
        super().clean()
        if self.user1.id == self.user2.id:
            raise ValidationError("You cannot initiate a chat with yourself.")

    @classmethod
    def create_thread(cls, sender_id, receiver_id): # Thread.get_or_create_thread
        # Always order the users so the smaller ID is user1
        sender_id, receiver_id = (sender_id, receiver_id) if sender_id < receiver_id else (receiver_id, sender_id)
        thread = cls.objects.create(user1_id=sender_id, user2_id=receiver_id)
        return thread # thread.save() to trigger auto_add during websocket disconnection.

class ThreadMessage(models.Model):
    thread = models.ForeignKey(
        ChatThread, 
        on_delete=models.CASCADE, 
        related_name="messages"
    )
    body = models.CharField(max_length=300)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="messages",
        related_query_name="message"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.get_full_name()} ({self.thread.id})"

    class Meta:
        ordering = ['-created_at']