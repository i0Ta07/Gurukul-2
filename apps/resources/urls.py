from django.urls import path
from apps.resources.views import CreateResource, DeleteResource, SearchResources

urlpatterns = [
    path("search/<int:org_id>", SearchResources.as_view(), name="search-resources"),
    path("create/<int:org_id>",CreateResource.as_view(),name="create-resource"),
    path("delete/<int:org_id>/<int:resource_id>",DeleteResource.as_view(),name="delete-resource"),   
]