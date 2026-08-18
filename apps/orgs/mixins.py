from apps.orgs.models import Organization,OrgMembership
from apps.users.models import User
from apps.orgs.utils import is_owner_or_admin,is_owner,is_admin_or_teacher,is_member
from django.shortcuts import get_object_or_404
from config.utils import create_message_and_redirect

class TeacherRequiredMixin:
    """Mixin that requires the user to be a teacher to access a page."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != User.UserType.TEACHER:
            return create_message_and_redirect(request,"Only Teachers can perform this action.","users-dashboard","warning",)

        return super().dispatch(request, *args, **kwargs)   

# Inserts root_org inside the View instance, so don't have to make multiple DB calls.
class RootOrganizationMixin:
    def get_root_org(self):
        if not hasattr(self, "_root_org"):
            org = get_object_or_404(
                Organization,
                pk=self.kwargs["org_id"],
            )
            self._root_org = org.get_root()
        return self._root_org
    
class OwnerAdminRequired(RootOrganizationMixin):
    """Mixin that requires the user to be a owner or admin to access any view of the org using org_id given in the request."""
    def dispatch(self, request, *args, **kwargs):
        root = self.get_root_org()
        role = is_owner_or_admin(root=root,user=request.user)
        if not role:
            return create_message_and_redirect(request,message="Only admins and owner can perform this action.",
                url="users-dashboard",code="error")
        self.role = role

        return super().dispatch(request, *args, **kwargs)    

class OwnerRequired(RootOrganizationMixin):
    """Mixin that requires the user to be a owner or admin to access any view of the org using org_id given in the request."""
    def dispatch(self, request, *args, **kwargs):
        root = self.get_root_org()
        role = is_owner(root=root,user=request.user)
        if not role:
            return create_message_and_redirect(request,message="Only owner can perform this action.",url="users-dashboard",code="error")
        self.role = role
        
        return super().dispatch(request, *args, **kwargs)   

class AdminTeacherRequired(RootOrganizationMixin):
    def dispatch(self, request, *args, **kwargs):
        root = self.get_root_org()
        role = is_admin_or_teacher(root=root,user=request.user)
        if not role:
            return create_message_and_redirect(request,"Only teachers and admins of this organization can perform this action","users-dashboard","warning",)
        self.role = role
        return super().dispatch(request, *args, **kwargs) 

class OrgMembershipRequiredMixin(RootOrganizationMixin):
    """Mixin that requires the user to be the member of the given organization given by org_id to perform some task."""
    def dispatch(self, request, *args, **kwargs):
        root = self.get_root_org()
        role  = is_member(root=root,user=request.user)
        if not role:
            return create_message_and_redirect(request,"You are not a part of this organization","users-dashboard","warning",)
        self.role = role
        return super().dispatch(request, *args, **kwargs) 