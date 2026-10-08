from django.db.models.signals import post_delete
from django.dispatch import receiver
from apps.content.models import Resource

@receiver(signal=post_delete,sender=Resource)
def delete_resource_file(sender, instance:Resource, **kwargs):
    if instance.file:
        instance.file.delete(save=False)