from django.contrib.auth.mixins import LoginRequiredMixin
from apps.orgs.mixins import TeacherRequiredMixin,OrgMembershipRequiredMixin
from django.shortcuts import get_object_or_404,render
from apps.orgs.models import Organization
from django.http import HttpResponseNotAllowed
from django.core.exceptions import ValidationError
from apps.classes.forms import CreateClassForm
from django.contrib import messages
from django.views import View
from apps.classes.utils import validate_classroom


# Create your views here.

# You can view all the classrooms in the present organization, but you can access if you are owner or have a membership.

class CreateClassroom(LoginRequiredMixin,OrgMembershipRequiredMixin,View):
    template_name = "classes/partials/create_class.html"
    form_class = CreateClassForm

    def get(self,request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form":form,"org_id":kwargs['org_id'],"org_path":kwargs['org_path']})

    
    def post(self, request, *args, **kwargs):
        parent_id = kwargs['org_id']
        parent_path = kwargs['org_path']

        parent = get_object_or_404(Organization, pk=parent_id)

        # Load post data into the form
        form = self.form_class(request.POST)
        form_context = {"form":form,"org_id":kwargs['org_id'],"org_path":kwargs['org_path']}
        if not form.is_valid():
            return render(request, self.template_name,form_context)

        print(parent)
        classroom = form.save(commit=False)
        classroom.parent_org = parent
        classroom.owner = request.user
        try:
            validate_classroom(parent = parent, instance=classroom)
        except ValidationError as e:
            form.add_error(field=None,error=e.message)
            return render(request, self.template_name,form_context)
        classroom.save()
        path = f"{parent_path}/{classroom.slug}"
        row_context = {
            "classroom":{ "name":classroom.name,"path":path}
        }
        messages.success(request,message="Classroom created successfully.")
        response = render(request, "orgs/list_orgs.html#classroom-row",row_context)
        response['HX-Trigger'] = 'classroom-created'
        return response

class ViewClassroom(LoginRequiredMixin,View): # class membership for students. or membership of teacher or owner of class
    pass