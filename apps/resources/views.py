from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q,Exists, OuterRef
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from apps.classes.mixins import ClassroomOrgMembershipRequired
from apps.classes.models import ClassMembership, Classroom
from apps.orgs.models import Organization
from apps.orgs.utils import OrgUserType
from apps.resources.forms import ResourceForm, SearchResourceForm,OrgFilterForm
from apps.orgs.mixins import OrgMembershipRequiredMixin, TeacherRequiredMixin
from apps.resources.mixins import ResourceOrgMembershipRequired
from apps.resources.models import Resource, ResourceClassMembership
from apps.resources.utils import render_message_from_modal_to_page
from django.db import IntegrityError

class SearchResources(OrgMembershipRequiredMixin,TeacherRequiredMixin,LoginRequiredMixin,View):
    template_name = "resources/search_resources.html"
    search_resource_form_class=SearchResourceForm
    org_fitler_form_class = OrgFilterForm

    def get(self,request,*args,**kwargs):
        root,_ = self.get_root_current_org()
        search_resource_form = self.search_resource_form_class()
        org_fitler_form = self.org_fitler_form_class(root_org = root.id)
        context = {'search_resource_form':search_resource_form,'org_fitler_form':org_fitler_form,'org_id':kwargs.get('org_id')}
        if request.htmx:
            return render(request,'resources/search_resources.html#search-resources',context)
        return render(request,self.template_name,context)

    def post(self,request,*args,**kwargs):
        root,_ = self.get_root_current_org()
        search_resource_form = self.search_resource_form_class(request.POST)
        org_fitler_form = self.org_fitler_form_class(request.POST,root_org = root.id)
        if not search_resource_form.is_valid() or not org_fitler_form.is_valid():
            return render(request,'resources/search_resources.html#search-resources',context = {
                'search_resource_form':search_resource_form,'org_fitler_form':org_fitler_form,'org_id':kwargs.get('org_id')
                }
            )
        
        org_filter_fields = {
            field: org_fitler_form.cleaned_data[field]
            for field in org_fitler_form.changed_data
        }

        if not org_filter_fields and not search_resource_form.cleaned_data['type'] and not search_resource_form.cleaned_data['title']:
            messages.error(request,"Need something to continue search. Name, type or fitler")
            return render(request,"partials/messages.html")

        resources = Resource.objects.filter(root_id = root.id)

        if org_filter_fields:
            resources = resources.filter(snapshots__contains=[org_filter_fields])

        if search_resource_form.cleaned_data['type']:
            resources = resources.filter(type__in=search_resource_form.cleaned_data['type'])

        if search_resource_form.cleaned_data['title']:
            resources = resources.filter(title__icontains=search_resource_form.cleaned_data['title'])

        return render(request,'resources/search_resources.html#render-results',context={'resources':resources,'org_id':root.id})

class DeleteResource(LoginRequiredMixin,TeacherRequiredMixin,OrgMembershipRequiredMixin,ResourceOrgMembershipRequired,View):
    def get(self,request,*args,**kwargs):
        resource = self.resource
        if self.role not in [OrgUserType.ADMIN,OrgUserType.OWNER] and resource.created_by_id != request.user.id:
            return HttpResponse("<p class='text-center'>You do not have permission to delete this resource</p>",status=200)
        
        if ResourceClassMembership.objects.filter(resource_id=resource.id).exists():
            return HttpResponse("<p class='text-center'>This resource is attached to a classroom. You cannot delete it</p>",status=200)
        
        return render(request,"resources/partials/delete_resource.html",context= {'resource_title':resource.title,'resource_id':resource.id,'org_id':resource.root_id})

    def post(self,request,*args,**kwargs):
        resource = self.resource
        if self.role not in [OrgUserType.ADMIN,OrgUserType.OWNER] and resource.created_by_id != request.user.id:
            messages.error(request,"You do not have permission to delete this resource")
            return render_message_from_modal_to_page(request)
        if ResourceClassMembership.objects.filter(resource_id=resource.id).exists():
            messages.error(request,"This resource is attached to a classroom. You cannot delete it")
            return render_message_from_modal_to_page(request)

        resource.delete()
        response = HttpResponse("",status=200)
        return response

class CreateResource(LoginRequiredMixin,TeacherRequiredMixin,OrgMembershipRequiredMixin,View):
    form_class = ResourceForm
    template_name = "resources/create_resource.html"
    template_partial_name = "resources/create_resource.html#create-resource"

    def get(self,request,*args,**kwargs):
        root,_ = self.get_root_current_org()
        form  =self.form_class()
        context = {'org_id':root.id,'form':form,'org_name':root.name}
        if request.htmx:
            return render(request,self.template_partial_name,context)
        return render(request,self.template_name,context)

    def post(self,request,*args,**kwargs):
        root,_ = self.get_root_current_org()
        form  = self.form_class(request.POST,request.FILES)
        if not form.is_valid():
            return render(request,self.template_partial_name,{'org_id':root.id,'form':form,'org_name':root.name})

        resource = form.save(commit=False)
        resource.created_by_id = request.user.id
        resource.root_id = root.id
        resource.save()
        messages.success(request,"Resource saved successfully")
        return render(request,self.template_partial_name,{'org_id':root.id,'form':self.form_class(),'org_name':root.name})

class UpdateResource(LoginRequiredMixin,TeacherRequiredMixin,OrgMembershipRequiredMixin,ResourceOrgMembershipRequired,View):
    template_name="resources/partials/update_resource.html"
    form_class = ResourceForm

    def get(self,request,*args,**kwargs):
        root,_ = self.get_root_current_org()
        resource = self.resource
        if self.role not in [OrgUserType.ADMIN,OrgUserType.OWNER] and resource.created_by_id != request.user.id:
            return HttpResponse("<p class='text-center'>You do not have permission to update this resource</p>",status=200)

        form = self.form_class(instance=resource)
        return render(request,self.template_name,context={'form':form,'org_id':root.id,'resource_id':resource.id})

    def post(self,request,*args,**kwargs):
        root,_ = self.get_root_current_org()
        resource = self.resource
        if self.role not in [OrgUserType.ADMIN,OrgUserType.OWNER] and resource.created_by_id != request.user.id:
            return HttpResponse("<p class='text-center'>You do not have permission to update this resource</p>",status=200)
        
        form = self.form_class(request.POST,request.FILES,instance=resource) 
        if not form.is_valid():
            return render(request,self.template_name,context={'form':form,'org_id':root.id,'resource_id':resource.id})

        resource = form.save()
        response =  render(request,"resources/search_resources.html#resource",context={'resource':resource,'org_id':root.id})
        response['HX-Trigger'] = 'resource-updated'
        return response

class ListClassroomsToAttachResource(LoginRequiredMixin,TeacherRequiredMixin,OrgMembershipRequiredMixin,ResourceOrgMembershipRequired,View):
    def get(self,request,*args,**kwargs):
        root,_ = self.get_root_current_org()

        if self.role in [OrgUserType.ADMIN,OrgUserType.OWNER]:
            leafs = Organization.objects.get_descendants(root).filter(numchild=0)
            classrooms = Classroom.objects.filter(parent__in=leafs).distinct().select_related('parent')

        else:
            classrooms = Classroom.objects.filter(Q(membership__user_id = request.user.id,membership__status = 'A') | Q(owner_id = request.user.id)).distinct().select_related('parent')

        resource = self.resource

        attached = ResourceClassMembership.objects.filter(
            resource_id=self.resource.id,
            classroom_id=OuterRef('pk'),
        )

        # Queries are lazily evaluated, hence we will only run one query. We keep on adding the filters and conditions.
        classrooms = classrooms.annotate(
            is_attached=Exists(attached)
        ).filter(is_attached=False)

        context = {'classrooms':classrooms,"org_id":root.id,"resource_id":resource.id}
        return render(request,"resources/partials/list_classrooms_to_attach_resource.html",context=context)

class AttachResource(LoginRequiredMixin,TeacherRequiredMixin,OrgMembershipRequiredMixin,ResourceOrgMembershipRequired,ClassroomOrgMembershipRequired,View):
    def post(self,request,*args,**kwargs):
        classroom,resource = self.classroom,self.resource
        if self.role not in [OrgUserType.ADMIN,OrgUserType.OWNER] and classroom.owner_id != request.user.id and not ClassMembership.objects.filter(classroom_id=classroom.id,user_id=request.user.id).exists():
            return HttpResponse("<p class='text-center'>You do not have permissions to attach resources to this classroom.</p>")

        try:
            _ = ResourceClassMembership.objects.create(
                classroom_id=classroom.id,
                resource_id=resource.id,
                created_by_id=request.user.id
            )
        except IntegrityError:
            return HttpResponse("<p class='text-center text-green-500'>This resource is already attached to this classroom.</p>")

        messages.success(request,f"{resource.title} is successfully attached to {classroom.name}")
        response = render_message_from_modal_to_page(request)
        response['HX-Trigger'] = 'resource-attached'
        return response

class DetachResource(LoginRequiredMixin,TeacherRequiredMixin,OrgMembershipRequiredMixin,ResourceOrgMembershipRequired,ClassroomOrgMembershipRequired,View):
    def get(self,request,*args,**kwargs):
        root,_ = self.get_root_current_org()
        classroom,resource = self.classroom,self.resource
        if self.role not in [OrgUserType.ADMIN,OrgUserType.OWNER] and classroom.owner_id != request.user.id and not ClassMembership.objects.filter(classroom_id=classroom.id,user_id=request.user.id).exists():
            return HttpResponse("<p class='text-center'>You do not have permissions to detach resources to this classroom.</p>")
        context = {'resource_id':resource.id,'classroom_id':classroom.id,'org_id':root.id,'resource_title':resource.title,'classroom_name':classroom.name}
        return render(request,"resources/partials/detach_resource.html",context)

    def post(self,request,*args,**kwargs):
        classroom,resource = self.classroom,self.resource
        if self.role not in [OrgUserType.ADMIN,OrgUserType.OWNER] and classroom.owner_id != request.user.id and not ClassMembership.objects.filter(classroom_id=classroom.id,user_id=request.user.id).exists():
            return HttpResponse("<p class='text-center'>You do not have permissions to detach resources to this classroom.</p>")

        res_mem = get_object_or_404(ResourceClassMembership,resource_id=resource.id,classroom_id=classroom.id)
        res_mem.delete()
        response = HttpResponse()
        response['HX-Trigger'] = 'resource-detached'
        return response