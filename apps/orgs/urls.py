from django.urls import path
from .views import org_detail,org_index, create_org,create_classroom

urlpatterns = [
    path("", org_index, name="org-index"),
    path("create/<int:org_id>/", create_org, name="create-org"),
    # path("edit/org/<int:org_id>/", edit_org, name="org-edit"),
    path("create/classroom/<int:org_id>/", create_classroom, name="create-classroom"),
    # path("<path:class_path>", classroom_detail, name="classroom-detail"), 

    # Catches them all, has to below
    path("<path:org_path>/", org_detail, name="org-detail"),
]