from apps.orgs.models import Organization
from apps.classes.models import ClassMembership, Classroom
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from apps.users.models import User
from apps.orgs.utils import ClassUserType

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

def _get_user_class_role(classroom:Classroom,teacher:User):
    if classroom.owner_id  == teacher.id:
        return ClassUserType.OWNER
    elif ClassMembership.objects.filter(user_id = teacher.id,classroom_id = classroom.id).exists():
        return ClassUserType.TEACHER
    else:
        return None

def is_class_owner_or_teacher(classroom:Classroom,teacher:User):
    role = _get_user_class_role(classroom=classroom,teacher=teacher)
    if role:
        return role
    return None

def is_class_owner(classroom:Classroom,teacher:User):
    role = _get_user_class_role(classroom= classroom,teacher=teacher)
    if role == ClassUserType.OWNER:
        return role
    return None
        
