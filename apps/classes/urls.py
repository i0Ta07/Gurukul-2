from django.urls import path
from apps.classes.views import (
    CreateClassroom,ViewClassroomFromOrgs,ViewClassroomDetails,EditAnnouncement,DeleteAnnouncement,
    RenameClassroom,DeleteClassroom,ListClassrooms,ViewClassroomFromDashboard,JoinClassroom,CreateAnnouncement,
    ShareClassroom,CreateNewClassroomCode,ViewAllAnnouncements,ViewAllResources,ViewClassroomConfig,LeaveClassroom,
    TransferClassroomOwnership,RemoveStudentFromClassroom,RemoveTeacherFromClassroom
)

urlpatterns = [
    path("create/classroom/<path:parent_org_path>/<int:parent_org_id>/", CreateClassroom.as_view(), name="create-classroom"),
    path("view/details/<int:parent_org_id>/<int:classroom_id>", ViewClassroomDetails.as_view(), name="view-classroom-details"),
    path("rename/<path:parent_org_path>/<int:parent_org_id>/<int:classroom_id>",RenameClassroom.as_view(),name='rename-classroom'),
    path("delete/<int:parent_org_id>/<int:classroom_id>",DeleteClassroom.as_view(),name = "delete-classroom"),
    path("list/classrooms/", ListClassrooms.as_view(), name="list-classrooms"), 
    path("join/<str:code>",JoinClassroom.as_view(),name="join-classroom"),
    path("create/announcement/<int:classroom_id>",CreateAnnouncement.as_view(),name="create-announcement"),
    path("edit/announcement/<int:announcement_id>",EditAnnouncement.as_view(),name="edit-announcement"),
    path("delete/announcement/<int:announcement_id>",DeleteAnnouncement.as_view(),name="delete-announcement"),
    path("share/classroom/<int:org_id>/<int:classroom_id>",ShareClassroom.as_view(),name="share-classroom"),
    path("create/new/classroom/code/<int:org_id>/<int:classroom_id>",CreateNewClassroomCode.as_view(),name="create-new-classroom-code"),
    path("view/all/announcements/<int:org_id>/<int:classroom_id>/<int:page>",ViewAllAnnouncements.as_view(),name='view-all-announcements'),
    path("view/all/resources/<int:org_id>/<int:classroom_id>/<int:page>",ViewAllResources.as_view(),name='view-all-resources'),
    path("view/config/<int:org_id>/<int:classroom_id>",ViewClassroomConfig.as_view(),name='view-classroom-config'),
    path("leave/classroom/<int:classroom_id>",LeaveClassroom.as_view(),name='leave-classroom'),
    path("transfer/ownership/<int:org_id>/<int:classroom_id>",TransferClassroomOwnership.as_view(),name='transfer-classroom-ownership'),
    path("remove/student/<int:org_id>/<int:classroom_id>/<int:student_id>",RemoveStudentFromClassroom.as_view(),name='remove-student-from-classroom'),
    path("remove/teacher/<int:org_id>/<int:classroom_id>/<int:teacher_id>",RemoveTeacherFromClassroom.as_view(),name='remove-teacher-from-classroom'),


    path("classroom/<path:slug>/<int:classroom_id>", ViewClassroomFromDashboard.as_view(), name="view-classroom-dashboard"),
    path("<path:classroom_path>/<int:parent_org_id>/<int:classroom_id>", ViewClassroomFromOrgs.as_view(), name="view-classroom-orgs"),
]