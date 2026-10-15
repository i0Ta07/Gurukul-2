from django.urls import path
from apps.classes.views import (
    CreateClassroom,ViewClassroomFromOrgs,ViewClassroomDetails,EditAnnouncement,DeleteAnnouncement,
    RenameClassroom,DeleteClassroom,ListClassrooms,ViewClassroomFromDashboard,JoinClassroom,CreateAnnouncement
)

urlpatterns = [
    path("create/classroom/<path:parent_org_path>/<int:parent_org_id>/", CreateClassroom.as_view(), name="create-classroom"),
    path("view/details/<int:parent_org_id>/<int:classroom_id>", ViewClassroomDetails.as_view(), name="view-classroom-details"),
    path("rename/<path:parent_org_path>/<int:parent_org_id>/<int:classroom_id>",RenameClassroom.as_view(),name='rename-classroom'),
    path("delete/<int:parent_org_id>/<int:classroom_id>",DeleteClassroom.as_view(),name = "delete-classroom"),
    path("list/classrooms/", ListClassrooms.as_view(), name="list-classrooms"), 
    path("join/<str:code>",JoinClassroom.as_view(),name="join-classroom"),
    path("<int:classroom_id>", ViewClassroomFromDashboard.as_view(), name="view-classroom-dashboard"),
    path("create/announcement/<int:classroom_id>",CreateAnnouncement.as_view(),name="create-announcement"),
    path("edit/announcement/<int:classroom_id>/<int:announcement_id>",EditAnnouncement.as_view(),name="edit-announcement"),
    path("delete/announcement/<int:classroom_id>/<int:announcement_id>",DeleteAnnouncement.as_view(),name="delete-announcement"),


    path("<path:classroom_path>/<int:parent_org_id>/<int:classroom_id>", ViewClassroomFromOrgs.as_view(), name="view-classroom-orgs"),
]