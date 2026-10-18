from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View
from apps.resources.forms import SearchResourceForm,OrgFilterForm
from apps.orgs.mixins import OrgMembershipRequiredMixin, TeacherRequiredMixin
from apps.resources.models import Resource

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

        return render(request,'resources/search_resources.html#render-results',context={'resources':resources})
