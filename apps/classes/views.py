from config.mixins import TeacherRequiredMixin
from django.shortcuts import get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from apps.orgs.models import Organization
from django.http import HttpResponseNotAllowed
from django.core.exceptions import ValidationError
from apps.classes.forms import CreateClassForm
from django.contrib import messages

# Create your views here.

# You can view all the classes in the present organization, but you can access if you are owner or have a membership.

@login_required
def create_classroom(request, org_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    org = get_object_or_404(Organization, pk=org_id)

    form = CreateClassForm(request.POST)

    if form.is_valid():
        classroom = form.save(commit=False)
        classroom.org = org
        classroom.created_by = request.user

        try:
            classroom.save()
            messages.success(request, "Classroom created successfully.")
        except ValidationError as e:
            messages.error(request, e.message)

    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    return redirect("org-detail", org_path=org.path)
