from django.db.models.signals import post_delete
from django.dispatch import receiver
from apps.users.models import User

@receiver(signal=post_delete,sender=User)
def delete_profile_photo(sender, instance:User, **kwargs):
    if instance.profile_photo:
        instance.profile_photo.delete(save=False)