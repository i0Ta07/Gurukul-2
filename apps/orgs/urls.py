from django.urls import path
from apps.orgs.views import ViewOrgs, CreateChildOrg,CreateRootOrgAndConfig

urlpatterns = [
    path("", ViewOrgs.as_view(), name="view-orgs"),
    path("create/<path:org_path>/<int:org_id>/", CreateChildOrg.as_view(), name="create-child-org"),
    path("create/root/",CreateRootOrgAndConfig.as_view(),name='create-root-org'),
    # path("edit/org/<int:org_id>/", edit_org, name="org-edit"),
    
    # Catches them all, has to be last
    path("<path:org_path>/", ViewOrgs.as_view(), name="view-orgs"),
]