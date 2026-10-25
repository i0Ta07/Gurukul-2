from django.contrib import messages
from django.shortcuts import get_object_or_404
from apps.orgs.utils import OrgUserType, render_error_inside_modal
from apps.resources.utils import render_message_from_modal_to_page
from config.utils import create_message_and_redirect
from apps.orgs.mixins import OrgMembershipRequiredMixin, RootOrganizationMixin
from apps.resources.models import Resource

class ResourceRequiredMixin:
    def get_resource(self):
        if not hasattr(self,"_resource"):
            self._resource = get_object_or_404(Resource,pk= self.kwargs['resource_id'])
        return self._resource

class ResourceOrgMembershipRequired(ResourceRequiredMixin,RootOrganizationMixin):
    """Mixin that maps the reosurce_id to the given org_id. Checks if the resource belongs to the organization."""
    def dispatch(self, request, *args, **kwargs):
        root,_ = self.get_root_current_org()
        resource = self.get_resource()
        if resource.root_id != root.id:
            return create_message_and_redirect(request,message="The given resource does not belong to this organization", url="users-dashboard",code="error")
        return super().dispatch(request, *args, **kwargs)
