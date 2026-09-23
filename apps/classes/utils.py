from apps.orgs.models import Organization
from apps.classes.models import ClassMembership, Classroom
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from apps.users.models import User
from enum import StrEnum

class ClassUserType(StrEnum):
    OWNER = "Classroom Owner"
    TEACHER  = "Teacher"
    STUDENT = "Student"

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

def _get_user_class_role(classroom:Classroom,user:User):
    if classroom.owner_id  == user.id:
        return ClassUserType.OWNER
    elif ClassMembership.objects.filter(user_id = user.id,classroom_id = classroom.id).exists():
        if user.user_type == User.UserType.TEACHER:
            return ClassUserType.TEACHER
        elif user.user_type == User.UserType.STUDENT:
            return ClassUserType.STUDENT
    else:
        return False

def is_class_owner_or_teacher(classroom:Classroom,user:User):
    role = _get_user_class_role(classroom=classroom,user=user)
    if role != ClassUserType.STUDENT:
        return role
    return False

def is_student(classroom:Classroom, student: User):
    role = _get_user_class_role(classroom=classroom,user= student)
    if role == ClassUserType.STUDENT:
        return role
    return False

def is_member(classroom:Classroom,user:User):
    role = _get_user_class_role(classroom=classroom,user=user)
    if role:
        return role
    return False

def is_class_owner(classroom:Classroom,teacher:User):
    role = _get_user_class_role(classroom= classroom,user=teacher)
    if role == ClassUserType.OWNER:
        return role
    return False
        
