from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from apps.classes.models import ClassMembership, Classroom
from apps.orgs.mixins import OrgMembershipRequiredMixin, TeacherRequiredMixin, StudentRequiredMixin
from apps.classes.mixins import ClassroomOwnerOrgAdminOwnerRequired,ClassroomOwnerTeacherOrgAdminOwnerRequired,ClassroomStudentRequired
from django.shortcuts import get_object_or_404,render
from django.core.exceptions import ValidationError
from apps.classes.forms import ClassroomNameForm
from django.contrib import messages
from django.views import View
from apps.classes.utils import validate_classroom,validate_unique_classroom_siblings
from apps.orgs.utils import OrgUserType, render_error_inside_modal, build_slug
from apps.classes.utils import ClassUserType
from apps.chats.models import ChatRoom
from django.db import transaction


# You can view all the classrooms in the present organization, but you can access if you are owner/admin or is the owner of the class.

class CreateClassroom(LoginRequiredMixin,OrgMembershipRequiredMixin,View):
    template_name = "classes/partials/create_classroom.html"
    form_class = ClassroomNameForm

    def get(self,request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form":form,**kwargs})
    
    def post(self, request, *args, **kwargs):
        parent_org_path = kwargs['parent_org_path']
        _,parent = self.get_root_current_org()

        # Load post data into the form
        form = self.form_class(request.POST)
        form_context = {"form":form,**kwargs}
        if not form.is_valid():
            return render(request, self.template_name,form_context)

        classroom = form.save(commit=False)
        classroom.parent = parent
        classroom.owner = request.user
        try:
            validate_classroom(parent = parent, instance=classroom)
        except ValidationError as e:
            form.add_error(field=None,error=e.message)
            return render(request, self.template_name,form_context)
        with transaction.atomic(): 
            classroom.save()
            _ = ChatRoom.objects.create(classroom_id = classroom.id)

        row_context = {
            "classroom":build_slug(instance=classroom,parent_org_path=parent_org_path,role = ClassUserType.OWNER),**kwargs
        }
        messages.success(request,message="Classroom created successfully.")
        response = render(request, "orgs/view_orgs_and_classrooms.html#classroom-row",row_context)
        response['HX-Trigger'] = 'classroom-created'
        return response

class ViewClassroomTeacher(LoginRequiredMixin,TeacherRequiredMixin,ClassroomOwnerTeacherOrgAdminOwnerRequired,View): # class membership for students. or membership of teacher or owner of class
    template_name = "classes/classroom.html"
    def get(self,request, *args,**kwargs):
        role = self.role
        classroom = self.get_classroom()
        context = {"role":role,"classroom_name":classroom.name}
        if request.htmx:
            return render(request,"classes/classroom.html#classroom",context=context)
        return render(request=request,template_name=self.template_name,context=context)

class ViewClassroomDetails(LoginRequiredMixin,TeacherRequiredMixin,OrgMembershipRequiredMixin,View):
    template_name = "classes/partials/view_classroom_details.html"
    def get(self,request,*args,**kwargs):
        classroom = get_object_or_404(Classroom,id=kwargs['classroom_id'])
        return render(request,self.template_name,{"classroom":classroom})

class RenameClassroom(LoginRequiredMixin,TeacherRequiredMixin,ClassroomOwnerOrgAdminOwnerRequired,View):
    template_name = "classes/partials/rename_classroom.html"
    form_class = ClassroomNameForm
    def get(self,request,*args,**kwargs):
        classroom =  self.get_classroom()
        form = self.form_class(initial={'name':classroom.name})
        return render(request,self.template_name,{'form':form,**kwargs})

    def post(self,request,*args,**kwargs):
        form = self.form_class(request.POST)
        if not form.is_valid():
            return render_error_inside_modal(request,self.template_name,{'form':form,**kwargs})

        _,parent = self.get_root_current_org()
        classroom = self.get_classroom()
        classroom.name = form.cleaned_data['name']
        parent_org_path = kwargs['parent_org_path']
        try:
            validate_unique_classroom_siblings(parent = parent,instance=classroom)
        except ValidationError as e:
            form.add_error(field=None,error=e.message)
            return render_error_inside_modal(request,self.template_name,{'form':form,**kwargs})
        classroom.save()
        if self.role in [OrgUserType.ADMIN,OrgUserType.OWNER]:
            row_context = {
                "classroom":build_slug(instance=classroom,parent_org_path=parent_org_path),'role':self.role,**kwargs
            }
        elif self.role  == ClassUserType.OWNER:
            row_context = {
                "classroom":build_slug(instance=classroom,parent_org_path=parent_org_path,role = ClassUserType.OWNER),**kwargs
            }            
        response =  render(request,"orgs/view_orgs_and_classrooms.html#classroom-row",row_context)
        response['HX-Trigger'] = 'classroom-renamed'
        return response
        # Check if name is unique
        # classroom rename trigger
# Also check if the user is owner or admin of org.

class DeleteClassroom(LoginRequiredMixin,TeacherRequiredMixin,ClassroomOwnerOrgAdminOwnerRequired,View):
    template_name = "classes/partials/delete_classroom.html"
    def get(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        membership_count = ClassMembership.objects.filter(classroom= classroom).exists()
        if membership_count:
            return HttpResponse(
                "<p class='text-center'>This classroom can’t be deleted because students are still enrolled. Please flush the classroom first, then try deleting it again.<p>",
                status=200, 
            )
        else:
            return render(request,self.template_name,{"classroom_name":classroom.name,**kwargs})

    def post(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        classroom.delete()
        return HttpResponse("", status=200)

class ListClassrooms(LoginRequiredMixin,StudentRequiredMixin,View):
    template_name = "classes/list_classrooms.html"
    def get(self,request,*args, **kwargs):
        classrooms = Classroom.objects.filter(membership__user_id = request.user.id)
        context = {"classrooms":classrooms}
        if request.htmx:
            return render(request,"classes/list_classrooms.html#list-classrooms",context)
        return render(request,self.template_name,context)

class ViewClassroomStudent(LoginRequiredMixin,StudentRequiredMixin, ClassroomStudentRequired, View):
    template_name = "classes/classroom.html"
    def get(self,request, *args,**kwargs):
        role = self.role
        classroom = self.get_classroom()
        context = {"role":role,"classroom_name":classroom.name}
        if request.htmx:
            return render(request,"classes/classroom.html#classroom",context=context)
        return render(request=request,template_name=self.template_name,context=context)
