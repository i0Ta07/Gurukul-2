from django.urls import path
from apps.resources.views import SearchResources

urlpatterns = [
    path("search/<int:org_id>", SearchResources.as_view(), name="search-resources"),
]