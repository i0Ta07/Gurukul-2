from django.shortcuts import get_object_or_404
from apps.classes.models import Classroom
from config.utils import create_message_and_redirect
from apps.orgs.mixins import RootOrganizationMixin
from apps.orgs.utils import is_org_owner_or_admin
from apps.classes.utils import is_class_owner_or_teacher,is_class_owner,is_student

class ClassroomRequiredMixin:
    def get_classroom(self):
        if not hasattr(self,"_classroom"):
            self._classroom = get_object_or_404(Classroom,pk = self.kwargs['classroom_id'])
        return self._classroom

class ClassroomOwnerOrgAdminOwnerRequired(ClassroomRequiredMixin,RootOrganizationMixin):
    """Requires the user making the request to be either the owner of the classroom or owner/admin of the organization."""
    def dispatch(self, request, *args, **kwargs):
        root,_ = self.get_root_current_org()
        classroom = self.get_classroom()

        self.role = (
            is_org_owner_or_admin(
                root=root,
                user=request.user
            )
            or is_class_owner(
                classroom=classroom,
                teacher=request.user
            )
        )
        if not self.role:
            return create_message_and_redirect(request,message="Only classroom owner, Organization's Admins/Owners can perform this action.")
        return super().dispatch(request, *args, **kwargs)

class ClassroomOwnerTeacherOrgAdminOwnerRequired(ClassroomRequiredMixin,RootOrganizationMixin):
    def dispatch(self, request, *args, **kwargs):
        root, _ = self.get_root_current_org()
        classroom = self.get_classroom()

        self.role = (
            is_org_owner_or_admin(
                root=root,
                user=request.user
            )
            or is_class_owner_or_teacher(
                classroom=classroom,
                user=request.user
            )
        )

        if not self.role:
            return create_message_and_redirect(request,message=("Only classroom owners/teachers, Organization's Admins/Owners can perform this action."))

        return super().dispatch(request, *args, **kwargs)
    
class ClassroomStudentRequired(ClassroomRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        classroom = self.get_classroom()
        self.role = is_student(classroom = classroom, student = request.user)
        if not self.role:
            return create_message_and_redirect(request,message=("Only students that are part of this classroom can perform this action."))
        return super().dispatch(request, *args, **kwargs)