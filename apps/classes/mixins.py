from django.shortcuts import get_object_or_404
from apps.classes.models import Classroom
from config.utils import create_message_and_redirect
from apps.orgs.mixins import RootOrganizationMixin
from apps.orgs.utils import is_owner_or_admin,ClassUserType

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
        role = is_owner_or_admin(root=root,user=request.user)
        if role:
            self.role = role
        elif classroom.owner_id == request.user.id:
            self.role = ClassUserType.OWNER
        else:
            return create_message_and_redirect(request,message="Only classroom owner, Organization's Admins/Owners can perform this action.")
        return super().dispatch(request, *args, **kwargs)
