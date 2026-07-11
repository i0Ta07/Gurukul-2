from django.urls import path
from apps.classes.views import create_classroom

urlpatterns = [

    path("create/classroom/<int:org_id>/", create_classroom, name="create-classroom"),
    # path("<path:class_path>", classroom_detail, name="classroom-detail"), 

]