from django.urls import path
from apps.classes.views import CreateClassroom,ViewClassroom,ViewClassroomDetails

urlpatterns = [

    path("create/classroom/<path:org_path>/<int:org_id>/", CreateClassroom.as_view(), name="create-classroom"),
    path("<path:classroom_path>/", ViewClassroom.as_view(), name="view-classroom"),
    path("view/details/<int:parent_org_id>/<int:classroom_id>", ViewClassroomDetails.as_view(), name="view-classroom-details"),

    # path("<path:class_path>", classroom_detail, name="classroom-detail"), 

]