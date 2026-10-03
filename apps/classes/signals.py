from django.db.models.signals import post_delete
from django.dispatch import receiver
from apps.classes.models import Classroom

@receiver(signal=post_delete,sender=Classroom)
def delete_qr_code(sender, instance:Classroom, **kwargs):
    if instance.qr_code:
        instance.qr_code.delete(save=False)