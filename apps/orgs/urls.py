from django.urls import path
from apps.orgs.views import (
    ViewChildOrgs, CreateChildOrg,CreateRootOrgAndConfig,
    SendInvitations,SendBulkInvitations,ViewRootOrgs,
    CreateAdmins,ViewInvitations,ViewRootOrgConfig,
    ViewOrgDetails,DeleteChildOrg,DeleteRootOrg,DeleteRootOrgSendOTP,
    RevokeOrgMembership,RevokeOrgAdmin,RenameOrg
)

urlpatterns = [
    path("", ViewRootOrgs.as_view(), name="view-root-orgs"),
    path("create/root/",CreateRootOrgAndConfig.as_view(),name='create-root-org'),

    path("view/root/<int:org_id>/",ViewRootOrgConfig.as_view(),name='view-root-config'),

    path("invite/teacher/<int:org_id>/",SendInvitations.as_view(),name='send-invitation'),
    path("invite/teachers/<int:org_id>/",SendBulkInvitations.as_view(),name='send-bulk-invitaions'),

    path("create/admin/<int:org_id>/",CreateAdmins.as_view(),name='create-admin'),

    path("invitations/",ViewInvitations.as_view(),name='view-invitations'),
    path("invitations/<int:invitation_id>/",ViewInvitations.as_view(),name='create-org-members'),

    path("view/details/<int:org_id>/",ViewOrgDetails.as_view(), name='view-org-details'),

    path("delete/<int:org_id>/",DeleteRootOrg.as_view(),name='delete-root-org'),
    path("delete/verify-otp/<int:org_id>/",DeleteRootOrgSendOTP.as_view(),name='delete-root-org-verify-otp'),
    path("delete/<path:parent_org_path>/<int:org_id>/",DeleteChildOrg.as_view(),name='delete-child-org'),

    path("revoke/membership/<int:org_id>/<int:teacher_id>/",RevokeOrgMembership.as_view(),name='revoke-org-membership'),
    path("revoke/admin/<int:org_id>/<int:admin_id>/",RevokeOrgAdmin.as_view(),name='revoke-org-admin'),

    # Should be first
    path("rename/root/<int:org_id>/",RenameOrg.as_view(),name='rename-root-org'),
    path("rename/<path:parent_org_path>/<int:org_id>/",RenameOrg.as_view(),name='rename-child-org'),

    # path("edit/org/<int:org_id>/", edit_org, name="org-edit"),
    
    # Catches them all, has to be last
    path("create/<path:org_path>/<int:org_id>/", CreateChildOrg.as_view(), name="create-child-org"),
    path("<path:org_path>/<int:org_id>", ViewChildOrgs.as_view(), name="view-child-orgs"),
]