from django.utils import timezone
from celery import shared_task
from apps.orgs.models import OrgInvitation
from datetime import timedelta

@shared_task
def delete_expired_invitations():
    """This task is attached to cron job(each day at 2AM) that deletes the expired invitations. """
    expiration_date = timezone.now() - timedelta(days=7)
    expired_invites = OrgInvitation.objects.filter(created_at__lte=expiration_date)
    if expired_invites:
        expired_invites.delete()
        return True
    return None