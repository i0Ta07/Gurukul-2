from apps.orgs.models import OrgInvitation
from apps.users.models import User
from django.core.cache import cache
from apps.orgs.utils import get_invitation_count_key

# remember to update count on creating and deleting org invites.
def invitation_count(request):
    if not request.user.is_authenticated:
        return {}

    if request.user.user_type != User.UserType.TEACHER:
        return {}

    key = get_invitation_count_key(user_id=request.user.id)
    count = cache.get(key,None)
    if count is None:
        count = OrgInvitation.objects.filter(
            to_user_id=request.user.id
        ).count()
        cache.set(key=key,value=count,timeout = 900)
    return {"invitation_count": count}