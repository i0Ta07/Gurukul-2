from django.utils import timezone
from celery import shared_task
from apps.chats.models import RoomMessage,ThreadMessage
from datetime import timedelta

@shared_task
def delete_expired_room_messages():
    """This task is attached to cron job(each day at 12:30 AM) that deletes the expired room messages"""
    expired_room_messages_date = timezone.now() - timedelta(days=30)
    expired_room_messages = RoomMessage.objects.filter(created_at__lte = expired_room_messages_date)
    if expired_room_messages:
        expired_room_messages.delete()
        return True
    return None

@shared_task
def delete_expired_thread_messages():
    """This task is attached to cron job(each day at 12 AM) that deletes the expired thread messages"""
    expired_thread_messages_date = timezone.now() - timedelta(days=7)
    expired_thread_messages = RoomMessage.objects.filter(created_at__lte = expired_thread_messages_date)
    if expired_thread_messages:
        expired_thread_messages.delete()
        return True
    return None