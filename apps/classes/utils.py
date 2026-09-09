from apps.orgs.models import Organization
from apps.classes.models import Classroom
from django.utils.text import slugify
from django.core.exceptions import ValidationError

def validate_unique_classroom_siblings(parent:Organization ,instance:Classroom,):
    duplicates = Classroom.objects.filter(parent=parent,slug = slugify(instance.name))

    if instance.pk:
        duplicates = duplicates.exclude(pk=instance.pk) # in case of rename 

    if duplicates.exists():
        raise ValidationError(f"A class named '{instance.name}' already exists within {parent.name}.")
    
def validate_classroom(parent:Organization,instance:Classroom):
    """
    Maintains the unique name of the classroom inside a parent organization
    Used in create and update both
    """
    if parent.get_children().exists():
        raise ValidationError('Classes cannot be created in the same folder in which orgs exist.')
       
    validate_unique_classroom_siblings(parent = parent,instance=instance)
