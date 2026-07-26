from django.urls import path
from apps.orgs.views import (
    ViewChildOrgs, CreateChildOrg,CreateRootOrgAndConfig,
    SendInvitations,SendBulkInvitations,ViewRootOrgs,
    CreateAdmins,ViewInvitations
)

urlpatterns = [
    path("", ViewRootOrgs.as_view(), name="view-root-orgs"),
    path("create/root/",CreateRootOrgAndConfig.as_view(),name='create-root-org'),

    path("invite/teacher/<int:org_id>/",SendInvitations.as_view(),name='send-invitation'),
    path("invite/teachers/<int:org_id>/",SendBulkInvitations.as_view(),name='send-bulk-invitaions'),

    path("create/admin/<int:org_id>/",CreateAdmins.as_view(),name='create-admin'),

    path("invitations/",ViewInvitations.as_view(),name='view-invitations'),
    path("invitations/<int:invitation_id>/",ViewInvitations.as_view(),name='create-org-members'),


    # path("edit/org/<int:org_id>/", edit_org, name="org-edit"),
    
    # Catches them all, has to be last
    path("create/<path:org_path>/<int:org_id>/", CreateChildOrg.as_view(), name="create-child-org"),
    path("<path:org_path>/", ViewChildOrgs.as_view(), name="view-child-orgs"),
]