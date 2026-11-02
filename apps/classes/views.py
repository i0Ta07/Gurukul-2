from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse
from apps.classes.models import Announcement, ClassMembership, Classroom
from apps.orgs.mixins import OrgMembershipRequiredMixin, TeacherRequiredMixin
from apps.classes.mixins import ClassroomOwnerOrgAdminOwnerRequired,ClassroomOwnerTeacherOrgAdminOwnerRequired,ClassroomMembershipRequired,ClassroomOwnerTeacherRequired, ClassroomMemberOrgAdminOwnerRequired
from django.shortcuts import get_object_or_404,render
from django.core.exceptions import ValidationError
from apps.classes.forms import AnnouncementForm, ClassroomNameForm
from django.contrib import messages
from django.views import View
from apps.classes.utils import validate_classroom,validate_unique_classroom_siblings
from apps.orgs.models import OrgMembership
from apps.orgs.utils import OrgUserType, build_slug
from apps.classes.utils import ClassUserType
from apps.chats.models import ChatRoom
from django.db import transaction
from apps.resources.models import ResourceClassMembership
from config.utils import render_message_to_page,render_template_inside_modal
from apps.users.models import User
from config.utils import create_message_and_redirect, get_website_context
from django.db.models import Q
from asgiref.sync import async_to_sync
from apps.users.utils import send_notifications,create_notifications, update_notification_icon
from django.utils import timezone
from datetime import timedelta
from config.utils import annotate_is_editable
import uuid
from django.core.paginator import Paginator

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
        website_context = get_website_context(request)
        with transaction.atomic(): 
            classroom.save(website_context=website_context)
            _ = ChatRoom.objects.create(classroom_id = classroom.id)

        row_context = {
            "classroom":build_slug(instance=classroom,parent_org_path=parent_org_path,role = ClassUserType.OWNER),**kwargs
        }
        messages.success(request,message="Classroom created successfully.")
        response = render(request, "orgs/view_orgs_and_classrooms.html#classroom-row",row_context)
        response['HX-Trigger'] = 'classroom-created'
        return response

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
            return render_template_inside_modal(request,self.template_name,{'form':form,**kwargs})

        _,parent = self.get_root_current_org()
        classroom = self.get_classroom()
        classroom.name = form.cleaned_data['name']
        parent_org_path = kwargs['parent_org_path']
        try:
            validate_unique_classroom_siblings(parent = parent,instance=classroom)
        except ValidationError as e:
            form.add_error(field=None,error=e.message)
            return render_template_inside_modal(request,self.template_name,{'form':form,**kwargs})
        classroom.save(update_fields={"name"})
        role = self.get_role()
        if role in [OrgUserType.ADMIN,OrgUserType.OWNER]:
            row_context = {
                "classroom":build_slug(instance=classroom,parent_org_path=parent_org_path),'role':role,**kwargs
            }
        elif role  == ClassUserType.OWNER:
            row_context = {
                "classroom":build_slug(instance=classroom,parent_org_path=parent_org_path,role = role),**kwargs
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

class ListClassrooms(LoginRequiredMixin,View):
    template_name = "classes/list_classrooms.html"
    def get(self,request,*args, **kwargs):
        classrooms = Classroom.objects.filter(Q(membership__user_id = request.user.id,membership__status = 'A') | Q(owner_id = request.user.id)).distinct()
        context = {"classrooms":classrooms}
        if request.htmx:
            return render(request,"classes/list_classrooms.html#list-classrooms",context)
        return render(request,self.template_name,context)

class BaseClassroomView(LoginRequiredMixin,View):
    template_name = "classes/classroom.html"
    def get(self,request, *args,**kwargs):
        role = self.get_role()
        classroom = self.get_classroom()
        announcements = Announcement.objects.filter(classroom_id = classroom.id).select_related('created_by').order_by('-created_at')
        announcements = annotate_is_editable(queryset=announcements,minutes=15)
        resource_memberships = ResourceClassMembership.objects.filter(classroom_id =classroom.id).select_related('resource','created_by').order_by('-created_at')
        context = {"role":role,"classroom_name":classroom.name,"announcements":announcements,'resource_memberships':resource_memberships,"classroom_id":classroom.id,"org_id":classroom.parent_id}
        if request.htmx:
            return render(request,"classes/classroom.html#classroom",context=context)
        return render(request=request,template_name=self.template_name,context=context)

class ViewClassroomFromOrgs(BaseClassroomView,TeacherRequiredMixin,ClassroomOwnerTeacherOrgAdminOwnerRequired): # class membership for students. or membership of teacher or owner of class
    pass
class ViewClassroomFromDashboard(BaseClassroomView,ClassroomMembershipRequired):
    pass

class CreateAnnouncement(ClassroomOwnerTeacherRequired,TeacherRequiredMixin,LoginRequiredMixin,View):
    template_name = "classes/partials/announcements/create_announcement.html"
    form_class = AnnouncementForm

    def get(self,request,*args,**kwargs):
        form = self.form_class()
        classroom = self.get_classroom()
        context  = {"form":form,"classroom_id":classroom.id}
        return render(request,template_name=self.template_name,context = context)

    def post(self,request,*args,**kwargs):
        form = self.form_class(request.POST)
        classroom = self.get_classroom()
        if not form.is_valid():
            return render(request,template_name=self.template_name,context = {"form":form,"classroom_id":classroom.id})

        announcement = form.save(commit=False)
        announcement.created_by_id = request.user.id
        announcement.classroom_id = classroom.id
        announcement.save()
        users_id = list(ClassMembership.objects.filter(classroom_id = classroom.id,status = ClassMembership.Status.ACCEPTED).values_list('user_id',flat=True))
        users_id.append(classroom.owner_id) # Add owner
        users_id.remove(request.user.id) # remove current user
        url_path = reverse('view-classroom-dashboard',kwargs={'slug':classroom.slug,'classroom_id':classroom.id})
        body = f"{request.user.get_full_name()}({self._classroom.name}) said {announcement.body}"
        async_to_sync(create_notifications)(users_id=users_id,body = body,url_path=url_path)
        async_to_sync(send_notifications)(users_id=users_id,body=body,url_path=url_path)
        async_to_sync(update_notification_icon)(users_id=users_id)
        announcement.is_editable = True
        response = render(request,template_name="classes/classroom.html#announcement",context = {'announcement':announcement,'classroom_id':classroom.id})
        return response

class JoinClassroom(LoginRequiredMixin,View):
    template_name = 'classes/join_classroom.html'
    def get(self,request,*args,**kwargs):
        code = kwargs.get("code")
        classroom = get_object_or_404(Classroom.objects.select_related('owner','parent'), code = code)
        if ClassMembership.objects.filter(user_id=request.user.id,classroom_id = classroom.id).exists():
            return create_message_and_redirect(request,message="You are already a member of this classroom.",url="users-dashboard",code="info")
        if request.user.id == classroom.owner_id:
            return create_message_and_redirect(request,message="Owners cannot join the classroom.",url='users-dashboard',code="info")
        root = classroom.parent.get_root()
        if request.user.user_type == User.UserType.TEACHER and not OrgMembership.objects.filter(org_id= root.id,teacher_id = request.user.id).exists():
            return create_message_and_redirect(request,message="You are not the part of the organization",url='users-dashboard',code="info")
        teachers = ClassMembership.objects.filter(user__user_type = User.UserType.TEACHER,classroom_id=classroom.id).values('user__first_name','user__last_name')
        student_count = ClassMembership.objects.filter(user__user_type = User.UserType.STUDENT,classroom_id=classroom.id).count()
        context = {'teachers':teachers,'classroom_name':classroom.name,'owner_name':classroom.owner.get_full_name(),'code':code,'student_count':student_count,"created_at":classroom.created_at,"ancestors":classroom.parent.get_ancestors()}
        return render(request,self.template_name,context)

    def post(self,request,*args,**kwargs):
        code = kwargs.get("code")
        classroom = get_object_or_404(Classroom.objects.select_related('owner','parent'), code = code)
        if ClassMembership.objects.filter(user_id=request.user.id,classroom_id = classroom.id).exists():
            return create_message_and_redirect(request,message="You are already a member of this classroom.",url="users-dashboard",code="info")
        if request.user.id == classroom.owner_id:
            return create_message_and_redirect(request,message="Owners cannot join the classroom.",url='users-dashboard',code="info")
        root = classroom.parent.get_root()
        if request.user.user_type == User.UserType.TEACHER and not OrgMembership.objects.filter(org_id= root.id,teacher_id = request.user.id).exists():
            return create_message_and_redirect(request,message="You are not the part of the organization",url='users-dashboard',code="info")
        membership = ClassMembership(user_id = request.user.id, classroom_id = classroom.id)
        try:
            membership.full_clean()
        except ValidationError as e:
            messages.error(request,e)
            return render(request,"partials/messages.html")
        membership.save()
        return create_message_and_redirect(request,message = f"You are now part of {membership.classroom.name}.",url="list-classrooms",code="success")

class EditAnnouncement(LoginRequiredMixin,View):
    form_class = AnnouncementForm
    template_name = "classes/partials/announcements/edit_announcement.html"
    def get(self,request,*args,**kwargs):
        announcement_id= kwargs.get('announcement_id')
        announcement = get_object_or_404(Announcement,pk = announcement_id)
        if announcement.created_by_id != request.user.id:
            return HttpResponse(
                "<p class='text-center'>You are not the author of this announcement.</p>",status=200,)
        if announcement.created_at <= timezone.now() - timedelta(minutes=15):
            return HttpResponse(
                "<p class='text-center'>You can only edit an announcement only after 15 minutes of creation..</p>",status=200,)      
        form = self.form_class(initial={'body':announcement.body})
        
        return render(request,template_name=self.template_name,context={'announcement_id':announcement_id,'form':form})

    def post(self,request,*args,**kwargs):
        announcement_id= kwargs.get('announcement_id')
        announcement = get_object_or_404(Announcement,pk = announcement_id)
        if announcement.created_by_id != request.user.id:
            return HttpResponse(
                "<p class='text-center'>You are not the author of this announcement.</p>",status=200,)
        if announcement.created_at <= timezone.now() - timedelta(minutes=15):
            return HttpResponse(
                "<p class='text-center'>You can only edit an announcement only after 15 minutes of creation.</p>",status=200,)
        form = self.form_class(request.POST)
        
        if not form.is_valid():
            return render(request,template_name=self.template_name,context={'announcement_id':announcement_id,'form':form})
        new_body = form.cleaned_data['body']
        announcement.body = new_body
        announcement.save(update_fields={'body'})
        announcement.is_editable = True
        response = render(request,'classes/classroom.html#announcement',context = {'announcement':announcement})
        response['HX-Trigger'] = 'announcement-edited'
        return response

class DeleteAnnouncement(LoginRequiredMixin,View):
    template_name = "classes/partials/announcements/delete_announcement.html"

    def get(self,request,*args,**kwargs):
        announcement_id= kwargs.get('announcement_id')
        announcement = get_object_or_404(Announcement,pk = announcement_id)
        if announcement.created_by_id != request.user.id:
            return HttpResponse(
                "<p class='text-center'>You are not the author of this announcement.</p>",status=200,)
        if announcement.created_at <= timezone.now() - timedelta(minutes=15):
            return HttpResponse(
                "<p class='text-center'>You can only delete an announcement only after 15 minutes of creation.</p>",status=200,)         
        
        return render(request,template_name=self.template_name,context={'announcement_id':announcement_id})

    def post(self,request,*args,**kwargs):
        announcement_id= kwargs.get('announcement_id')
        announcement = get_object_or_404(Announcement,pk = announcement_id)
        if announcement.created_by_id != request.user.id:
            return HttpResponse(
                "<p class='text-center'>You are not the author of this announcement.</p>",status=200,)
        if announcement.created_at <= timezone.now() - timedelta(minutes=15):
            return HttpResponse(
                "<p class='text-center'>You can only delete an announcement only after 15 minutes of creation.</p>",status=200,)
        announcement.delete()
        response = HttpResponse("", status=200)
        response['HX-Trigger'] = 'announcement-deleted'
        return response

class ShareClassroom(LoginRequiredMixin,TeacherRequiredMixin,ClassroomOwnerTeacherOrgAdminOwnerRequired,View):
    def get(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        root,_ = self.get_root_current_org()
        website_context = get_website_context(request)
        classroom_link = f"{website_context['protocol']}://{website_context['domain']}/classes/join/{classroom.code}"
        context = {'classroom_link':classroom_link,'classroom_qr_code':classroom.qr_code.url,'classroom_name':classroom.name,'classroom_id':classroom.id,'org_id':root.id}
        return render(request,"classes/partials/share_classroom.html",context)

class CreateNewClassroomCode(LoginRequiredMixin,TeacherRequiredMixin,ClassroomOwnerOrgAdminOwnerRequired,View):
    def post(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        classroom.code = uuid.uuid4()
        website_context = get_website_context(request)
        classroom.save(website_context=website_context,update_fields=['code'])
        response = HttpResponse("<p class='text-center'>New code has been generated. Please, close this modal.</p>")
        return response

class FlushClassroom(LoginRequiredMixin,TeacherRequiredMixin,ClassroomOwnerOrgAdminOwnerRequired,View):
    # delete class memberships announcements
    # set is_active = False for quizzes
    # verify OTP 
    pass

class ViewAllAnnouncements(LoginRequiredMixin,ClassroomMemberOrgAdminOwnerRequired,View):
    template_name= 'classes/view_all_announcements.html'
    def get(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        announcements =  classroom.announcements.all().select_related('created_by').order_by('-created_at')
        announcements = annotate_is_editable(queryset=announcements,minutes=15)
        p = Paginator(announcements,9)
        page = kwargs.get('page')
        page_obj = p.get_page(page)
        page_range = p.page_range
        last_page = len(page_range)
        context = {'current_page':page,'announcements':page_obj,'classroom_name':classroom.name,'classroom_id':classroom.id,'org_id':classroom.parent_id,'page_range':page_range}
        if len(page_range)> 1:
            context['previous'] = page-1 if page-1 > 1 else 1
            context['next'] = page+1 if page+1 <= last_page else page
            context['last_page'] = last_page
        if request.htmx:
            return render(request,'classes/view_all_announcements.html#view-all-announcements',context)
        return render(request,self.template_name,context)

class ViewAllResources(LoginRequiredMixin,ClassroomMemberOrgAdminOwnerRequired,View):
    template_name= "classes/view_all_resources.html"
    def get(self,request,*args,**kwargs):
        classroom = self.get_classroom()

        resource_memberships = classroom.resource_memberships.all().order_by('-created_by').select_related('resource','created_by').order_by('-created_at')
        p = Paginator(resource_memberships,10)
        page = kwargs.get('page')
        page_obj = p.get_page(page)
        page_range = p.page_range
        last_page = len(page_range)
        context = {'current_page':page,'resource_memberships':page_obj,'classroom_name':classroom.name,'org_id':classroom.parent_id,'classroom_id':classroom.id,'page_range':page_range,'org_id':classroom.parent_id}
        if len(page_range)> 1:
            context['previous'] = page-1 if page-1 > 1 else 1
            context['next'] = page+1 if page+1 <= last_page else page
            context['last_page'] = last_page
        if request.htmx:
            return render(request,'classes/view_all_resources.html#view-all-resources',context)
        return render(request,self.template_name,context)

class ViewClassroomConfig(LoginRequiredMixin,ClassroomMemberOrgAdminOwnerRequired,View):
    template_name = "classes/view_classroom_config.html"
    def get(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        owner_name = classroom.owner.get_full_name()
        memberships = ClassMembership.objects.filter(
            status=ClassMembership.Status.ACCEPTED,
            classroom_id=classroom.id
        ).select_related('user').only('user__first_name', 'user__last_name','created_at')
        teachers_memberships = memberships.filter(user__user_type = User.UserType.TEACHER)
        students_memberships = memberships.filter(user__user_type = User.UserType.STUDENT)
        role = self.get_role()
        
        is_admin_or_owner = True if role in [OrgUserType.ADMIN,OrgUserType.OWNER,ClassUserType.OWNER] else False
        is_owner = True if classroom.owner_id == request.user.id else False
        context = {
            'owner_name':owner_name,'teachers_memberships':teachers_memberships,
            'students_memberships':students_memberships,'classroom_name':classroom.name,
            'is_admin_or_owner':is_admin_or_owner,'classroom_id':classroom.id,
            'is_owner':is_owner,'role':role,'org_id':classroom.parent_id
        }
        if request.htmx:
            return render(request,'classes/view_classroom_config.html#view-classroom-config',context)
        return render(request,self.template_name,context)

class LeaveClassroom(LoginRequiredMixin,ClassroomMembershipRequired,View):

    def get(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        role = self.get_role()
        if role == ClassUserType.OWNER:
            return HttpResponse('You are the current owner of the classroom. To leave the classroom, make someone else a owner.')
        return render(request,'classes/partials/leave_classroom.html',{'classroom_name':classroom.name,'classroom_id':classroom.id})

    def post(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        role = self.get_role()
        if role == ClassUserType.OWNER:
            return HttpResponse('You are the current owner of the classroom. To leave the classroom, make someone else a owner.')
        membership = get_object_or_404(ClassMembership, classroom_id= classroom.id,user_id = request.user.id)
        membership.delete()
        return create_message_and_redirect(request,f'You are no longer part of {classroom.name}','users-dashboard',code="success")

class TransferClassroomOwnership(LoginRequiredMixin,ClassroomOwnerOrgAdminOwnerRequired,View):
    def get(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        teachers_memberships = ClassMembership.objects.filter(
            user__user_type = User.UserType.TEACHER,
            classroom_id=classroom.id).select_related('user').only('user__first_name', 'user__last_name')
        context = {'teachers_memberships':teachers_memberships,'classroom_id':classroom.id,'org_id':classroom.parent_id}
        return render(request,'classes/partials/transfer_classroom_ownership.html',context)

    def post(self,request,*args,**kwargs):
        classroom = self.get_classroom()
        new_owner_id = request.POST.get("new_owner_id")
        owner_membership = get_object_or_404(ClassMembership,classroom_id = classroom.id, user_id=new_owner_id)
        with transaction.atomic():
            owner_membership.delete()
            ClassMembership.objects.create(classroom_id=classroom.id,user_id=classroom.owner_id,)
            classroom.owner_id = new_owner_id
            classroom.save(update_fields=['owner'])
            
        return create_message_and_redirect(request,"Owner changed successfully",'users-dashboard',code="success")

class RemoveStudentFromClassroom(LoginRequiredMixin,ClassroomOwnerTeacherOrgAdminOwnerRequired,View):
    def get(self,request,*args,**kwargs):
        student_id = kwargs.get('student_id')
        user = get_object_or_404(User,pk=student_id)
        classroom = self.get_classroom()
        if not ClassMembership.objects.filter(user_id = user.id,classroom_id=classroom.id).exists():
            return HttpResponse("Given user is not the part of this classroom.")
        if user.user_type != User.UserType.STUDENT:
            return HttpResponse("Given user is not a student")
        context = {'classroom_name':classroom.name,'user_name':user.get_full_name(),'org_id':classroom.parent_id,'classroom_id':classroom.id,'user_id':user.id,'render_student_url':True}
        return render(request,'classes/partials/remove_user_from_classroom.html',context)
    
    def post(self,request,*args,**kwargs):
        student_id = kwargs.get('student_id')
        user = get_object_or_404(User,pk=student_id)
        if user.user_type != User.UserType.STUDENT:
            messages.error(request,"Given user is not a student")
            return render_message_to_page(request)
        classroom = self.get_classroom()
        membership = get_object_or_404(ClassMembership,user_id = user.id,classroom_id=classroom.id)
        membership.status = ClassMembership.Status.REVOKED
        membership.save(update_fields=['status'])
        return HttpResponse()

class RemoveTeacherFromClassroom(LoginRequiredMixin,ClassroomOwnerOrgAdminOwnerRequired,View):
    def get(self,request,*args,**kwargs):
        teacher_id = kwargs.get('teacher_id')
        user = get_object_or_404(User,pk=teacher_id)
        classroom = self.get_classroom()
        if not ClassMembership.objects.filter(user_id=user.id,classroom_id=classroom.id).exists():
            return HttpResponse("Given user is not the part of this classroom.")
        if user.user_type != User.UserType.TEACHER:
            return HttpResponse("Given user is not a teacher")
        context = {'classroom_name':classroom.name,'user_name':user.get_full_name(),'org_id':classroom.parent_id,'classroom_id':classroom.id,'user_id':user.id,'render_teacher_url':True}
        return render(request,'classes/partials/remove_user_from_classroom.html',context)

    def post(self,request,*args,**kwargs):
        teacher_id = kwargs.get('teacher_id')
        user = get_object_or_404(User,pk=teacher_id)
        if user.user_type != User.UserType.TEACHER:
            messages.error(request,"Given user is not a teacher")
            return render_message_to_page(request)
        classroom = self.get_classroom()
        membership = get_object_or_404(ClassMembership,user_id=user.id,classroom_id=classroom.id)
        membership.status = ClassMembership.Status.REVOKED
        membership.save(update_fields=['status'])
        return HttpResponse()
