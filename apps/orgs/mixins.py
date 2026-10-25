from apps.orgs.models import Organization
from apps.users.models import User
from apps.orgs.utils import is_org_owner_or_admin,is_org_owner,is_org_admin_or_teacher,is_org_member
from django.shortcuts import get_object_or_404
from config.utils import create_message_and_redirect
from abc import ABC, abstractmethod

class TeacherRequiredMixin:
    """Mixin that requires the user to be a teacher to access a page."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != User.UserType.TEACHER:
            return create_message_and_redirect(request,message="Only Teachers can perform this action.",url="users-dashboard",code="warning",)
        return super().dispatch(request, *args, **kwargs)

class StudentRequiredMixin:
    """Mixin that requires the user to be a student to access a page."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != User.UserType.STUDENT:
            return create_message_and_redirect(request,message="Only students can perform this action.",url="users-dashboard",code="warning",)
        return super().dispatch(request, *args, **kwargs)

# Inserts root_org inside the View instance, so don't have to make multiple DB calls.
class RootOrganizationMixin:
    """Base mixin to lazy load root,current org."""
    def get_root_current_org(self):
        "returns a tuple as (root,org)"
        if not hasattr(self, "_root_org") or not hasattr(self, "_org"):
            org_id = self.kwargs.get('org_id') or self.kwargs.get('parent_org_id')
            self._org  = get_object_or_404(Organization,pk=org_id)
            self._root_org = self._org.get_root()
        return self._root_org,self._org

class BaseOrgRoleRequiredMixin(RootOrganizationMixin,ABC):
    """Base mixin to handle organization role verification cleanly."""
    error_message = "You do not have permission to access this."

    @abstractmethod
    def check_role(self, root, user_id):
        """Override this in subclasses to use different verification functions."""
        pass

    def get_role(self):
        """Lazy-loaded role fetching to prevent execution-order dependencies."""
        if not hasattr(self, "_role"):
            root, _ = self.get_root_current_org()
            user_id = self.request.user.id
            self._role = self.check_role(root, user_id)
        return self._role

    def dispatch(self, request, *args, **kwargs):
        # Trigger role evaluation and check permission
        if not self.get_role():
            return create_message_and_redirect(
                request, 
                message=self.error_message, 
                url="users-dashboard", 
                code="error"
            )
            
        return super().dispatch(request, *args, **kwargs)
    
class OrgOwnerAdminRequired(BaseOrgRoleRequiredMixin):
    """User should be the owner/admin of the organization"""
    error_message = "Only admins and owner can perform this action."

    def check_role(self, root, user_id):
        """Requires the user to be the owner or an admin of the organization."""
        return is_org_owner_or_admin(root=root,user_id=user_id)

class OrgOwnerRequired(BaseOrgRoleRequiredMixin):
    """User should be the owner of the organization."""
    error_message = "Only owner can perform this action."

    def check_role(self, root, user_id):
        """Requires the user to be an owner of the organization."""
        return is_org_owner(root=root,user_id=user_id)

class AdminTeacherRequired(BaseOrgRoleRequiredMixin):
    """User should be the admin/teacher of the organization."""
    error_message = "Only teachers and admins of this organization can perform this action"

    def check_role(self, root, user_id):
        """Requires the user to be a teacher or an admin of the organization."""
        return is_org_admin_or_teacher(root=root,user_id=user_id)

class OrgMembershipRequiredMixin(BaseOrgRoleRequiredMixin):
    """User should be a member of the given organization"""
    error_message = "You are not a member of this organization"

    def check_role(self, root, user_id):
        """Requires the user to be a member of the organization."""
        return is_org_member(root=root,user_id=user_id)
