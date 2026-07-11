# Create teacherRequiredMixin

from django.shortcuts import redirect
from apps.users.models import User

class TeacherRequiredMixin:
    """Mixin that requires the user to be a teacher to access a page."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != User.UserType.TEACHER:
            return redirect("users-dashboard")

        return super().dispatch(request, *args, **kwargs)    