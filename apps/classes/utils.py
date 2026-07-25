from apps.orgs.models import Organization
from apps.classes.models import Classroom
from django.utils.text import slugify
from django.core.exceptions import ValidationError

def validate_classroom(parent:Organization,instance:Classroom):
    """
    Maintains the unique name of the classroom inside a parent organization
    Used in create and update both
    """
    if parent.get_children().exists():
        raise ValidationError('Classes cannot be created in the same folder in which orgs exist.')
       
    duplicates = Classroom.objects.filter(parent_org=parent,slug = slugify(instance.name))

    if instance.pk:
        duplicates = duplicates.exclude(pk=instance.pk) # in case of rename and edit

    if duplicates.exists():
        raise ValidationError(f"A class named '{instance.name}' already exists within {parent.name}.")