from django.urls import path
from .views import org_detail,org_index

urlpatterns = [
    path("", org_index, name="org-index"),
    path("<path:org_path>/", org_detail, name="org-detail"),
]