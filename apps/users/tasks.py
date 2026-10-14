from django.utils import timezone
from celery import shared_task
from apps.users.models import Notification
from datetime import timedelta

@shared_task
def delete_seen_notifications():
    """This task is attached to cron job(each day at 2AM) that deletes seen notifications. """
    notifications = Notification.objects.filter(is_seen = True)
    if notifications:
        notifications.delete()
        return True
    return None

@shared_task
def delete_expired_notifications():
    """This task is attached to cron job(each day at 2AM) to delete notifications after 3 days """
    expiration_date = timezone.now() - timedelta(days=3)
    expired_notifications = Notification.objects.filter(created_at__lte=expiration_date)
    if expired_notifications:
        expired_notifications.delete()
        return True
    return None