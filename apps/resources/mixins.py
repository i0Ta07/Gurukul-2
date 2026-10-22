from django.shortcuts import get_object_or_404
from config.utils import create_message_and_redirect
from apps.orgs.mixins import RootOrganizationMixin
from apps.resources.models import Resource

class ResourceOrgMembershipRequired(RootOrganizationMixin):
    """Mixin that maps the reosurce_id to the given org_id. Checks if the resource belongs to the organization."""
    def dispatch(self, request, *args, **kwargs):
        root,_ = self.get_root_current_org()
        resource_id = kwargs.get("resource_id")
        resource = get_object_or_404(Resource,pk = resource_id)
        if resource.root_id != root.id:
            return create_message_and_redirect(request,message="The given resource does not belong to this organization", url="users-dashboard",code="error")
        self.resource = resource
        return super().dispatch(request, *args, **kwargs)
