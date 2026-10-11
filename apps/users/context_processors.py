from apps.users.models import Notification
from django.core.cache import cache
from apps.users.utils import get_notification_count_key

# remember to update count on creating and deleting org invites.
def notification_count(request):
    if not request.user.is_authenticated:
        return {}

    key = get_notification_count_key(user_id=request.user.id)
    count = cache.get(key,None)
    if count is None:
        count = Notification.objects.filter(
            user_id=request.user.id
        ).count()
        cache.set(key=key,value=count,timeout = 900)
    return {"notification_count": count}
