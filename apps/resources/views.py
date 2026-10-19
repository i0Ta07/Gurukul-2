from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from apps.orgs.utils import OrgUserType
from apps.resources.forms import ResourceForm, SearchResourceForm,OrgFilterForm
from apps.orgs.mixins import OrgMembershipRequiredMixin, TeacherRequiredMixin
from apps.resources.models import Resource, ResourceClassMembership
from apps.resources.utils import render_message_from_modal_to_page

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

class DeleteResource(OrgMembershipRequiredMixin,TeacherRequiredMixin,LoginRequiredMixin,View):
    def get(self,request,*args,**kwargs):
        resource = get_object_or_404(Resource,pk=kwargs.get("resource_id"))
        if self.role not in [OrgUserType.ADMIN,OrgUserType.OWNER] and resource.created_by_id != request.user.id:
            return HttpResponse("<p class='text-center'>You do not have permission to delete this resource</p>",status=200)
        
        if ResourceClassMembership.objects.filter(resource_id=resource.id).exists():
            return HttpResponse("<p class='text-center'>This resource is attached to a classroom. You cannot delete it</p>",status=200)
        
        return render(request,"resources/partials/delete_resource.html",context= {'resource_title':resource.title,'resource_id':resource.id,'org_id':resource.root_id})

    def post(self,request,*args,**kwargs):
        resource = get_object_or_404(Resource,pk=kwargs.get("resource_id"))
        if self.role not in [OrgUserType.ADMIN,OrgUserType.OWNER] and resource.created_by_id != request.user.id:
            messages.error(request,"You do not have permission to delete this resource")
            return render_message_from_modal_to_page(request)
        if ResourceClassMembership.objects.filter(resource_id=resource.id).exists():
            messages.error(request,"This resource is attached to a classroom. You cannot delete it")
            return render_message_from_modal_to_page(request)

        resource.delete()
        response = HttpResponse("",status=200)
        return response