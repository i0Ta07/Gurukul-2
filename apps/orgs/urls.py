from django.urls import path
from apps.orgs.views import ViewChildOrgs, CreateChildOrg,CreateRootOrgAndConfig,SendInvitations,SendBulkInvitations,ViewRootOrgs

urlpatterns = [
    path("", ViewRootOrgs.as_view(), name="view-root-orgs"),
    path("create/<path:org_path>/<int:org_id>/", CreateChildOrg.as_view(), name="create-child-org"),
    path("create/root/",CreateRootOrgAndConfig.as_view(),name='create-root-org'),
    path("invite/teacher/<int:org_id>/",SendInvitations.as_view(),name='send-invitation'),
    path("invite/teachers/<int:org_id>/",SendBulkInvitations.as_view(),name='send-bulk-invitaions'),
    # path("edit/org/<int:org_id>/", edit_org, name="org-edit"),
    
    # Catches them all, has to be last
    path("<path:org_path>/", ViewChildOrgs.as_view(), name="view-child-orgs"),
]