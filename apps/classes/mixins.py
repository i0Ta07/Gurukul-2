from django.shortcuts import get_object_or_404
from apps.classes.models import Classroom
from config.utils import create_message_and_redirect
from apps.orgs.mixins import RootOrganizationMixin
from apps.orgs.utils import is_org_owner_or_admin
from apps.classes.utils import is_class_owner_or_teacher,is_class_owner,is_member,is_student
from abc import abstractmethod,ABC

class ClassroomRequiredMixin:
    """Base Mixin to lazy load the classroom."""
    def get_classroom(self):
        if not hasattr(self,"_classroom"):
            classroom_id = self.kwargs.get('classroom_id')
            self._classroom = get_object_or_404(Classroom,pk = classroom_id)
        return self._classroom

class ClassroomOrgMembershipRequired(RootOrganizationMixin,ClassroomRequiredMixin):
    """Given classroom should be a part of the organization"""
    def dispatch(self, request, *args, **kwargs):
        root,_ = self.get_root_current_org()
        classroom = self.get_classroom()
        parent_root = classroom.parent.get_root()
        if parent_root.id != root.id:
            return create_message_and_redirect(request,message="The given classroom does not belong to this organization", url="users-dashboard",code="error")
        return super().dispatch(request, *args, **kwargs)

class BaseClassroomRoleRequiredMixin(ClassroomRequiredMixin,ABC):
    """Base mixin to determine classroom role."""
    error_message = "You do not have permission to access this classroom."

    @abstractmethod
    def check_role(self, classroom, user):
        """Override this in subclasses to verify permissions using root, classroom, and user."""
        pass

    def get_role(self):
        """Lazy-loaded role fetching for classrooms and orgs."""
        if not hasattr(self, "_role"):
            classroom = self.get_classroom()
            self._role = self.check_role(classroom = classroom, user = self.request.user)
        return self._role

    def dispatch(self,request,*args,**kwargs):
        if not self.get_role():
            return create_message_and_redirect(
                request,
                message = self.error_message,
                url="users-dashboard", 
                code="error"
            )
        return super().dispatch(request, *args, **kwargs)

class BaseClassroomOrgRoleMixin(BaseClassroomRoleRequiredMixin,RootOrganizationMixin,ABC):
    """Base mixin to determine user role is within a classroom which is determined by either his organization role or classroom role."""
    
    @abstractmethod
    def check_role(self, root, classroom, user):
        """Override this in subclasses to verify permissions using root, classroom, and user."""
        pass

    def get_role(self):
        """Lazy-loaded role fetching for classrooms and orgs."""
        if not hasattr(self, "_role"):
            root, _ = self.get_root_current_org()
            classroom = self.get_classroom()
            parent_root = classroom.parent.get_root()
            if parent_root.id != root.id:
                return create_message_and_redirect(self.request,message="The given classroom does not belong to this organization", url="users-dashboard",code="error")
            self._role = self.check_role(root, classroom, self.request.user)
        return self._role


class ClassroomOwnerOrgAdminOwnerRequired(BaseClassroomOrgRoleMixin):
    """User should be classroom's owner or organization's admin/owner"""
    error_message = "Only classroom owners, Organization's Admins/Owners can perform this action."
    def check_role(self, root, classroom, user):
        return (
            is_org_owner_or_admin(root=root, user_id=user.id)
            or is_class_owner(classroom=classroom, teacher=user)
        )
    
class ClassroomOwnerTeacherOrgAdminOwnerRequired(BaseClassroomOrgRoleMixin):
    """User should be classroom's owner/teacher or organization's admin/owner"""
    error_message = "Only classroom owners/teachers, Organization's Admins/Owners can perform this action."
    def check_role(self, root, classroom, user):
        return (
            is_org_owner_or_admin(root=root, user_id=user.id)
            or is_class_owner_or_teacher(classroom=classroom,user=user)
        )

class ClassroomMemberOrgAdminOwnerRequired(BaseClassroomOrgRoleMixin):
    """User should be classroom's owner/teacher/student or organization's admin/owner"""
    error_message = "Only classroom owners/teachers/student, Organization's Admins/Owners can perform this action."
    def check_role(self, root, classroom, user):
        return (
            is_org_owner_or_admin(root=root, user_id=user.id)
            or is_member(classroom=classroom,user=user)
        )

class ClassroomStudentRequired(BaseClassroomRoleRequiredMixin):
    """User should be a student of the classroom """
    error_message = "Students that are part of this classroom can perform this action."
    def check_role(self, classroom, user):
        return is_student(classroom = classroom, user = user)
    

class ClassroomOwnerTeacherRequired(BaseClassroomRoleRequiredMixin):
    """User should classroom owner/teacher."""
    error_message = "Owner and teachers of this classroom can perform this action."
    def check_role(self, classroom, user):
        return is_class_owner_or_teacher(classroom = classroom, user = user)

class ClassroomMembershipRequired(BaseClassroomRoleRequiredMixin):
    """User should be part of the classroom."""
    error_message = "You are not a part of this classroom."
    def check_role(self, classroom, user):
        return is_member(classroom = classroom, user = user)
