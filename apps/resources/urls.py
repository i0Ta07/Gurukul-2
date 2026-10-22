from django.urls import path
from apps.resources.views import (CreateResource, DeleteResource, SearchResources, UpdateResource,
    ListClassroomsToAttachResource, AttachResource,DetachResource,ViewResourceHistory)

urlpatterns = [
    path("search/<int:org_id>", SearchResources.as_view(), name="search-resources"),
    path("create/<int:org_id>",CreateResource.as_view(),name="create-resource"),
    path("update/<int:org_id>/<int:resource_id>",UpdateResource.as_view(),name="update-resource"),
    path("delete/<int:org_id>/<int:resource_id>",DeleteResource.as_view(),name="delete-resource"),
    path("view/history/<int:org_id>/<int:resource_id>",ViewResourceHistory.as_view(),name="view-resource-history"),
    path("attach/<int:org_id>/<int:classroom_id>/<int:resource_id>",AttachResource.as_view(),name="attach-resource"),
    path("detach/<int:org_id>/<int:classroom_id>/<int:resource_id>",DetachResource.as_view(),name="detach-resource"),
    path("list/classerooms/attach/resource/<int:org_id>/<int:resource_id>",ListClassroomsToAttachResource.as_view(),name="list-classrooms-to-attach-resource"),
]