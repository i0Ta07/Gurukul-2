from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View
from apps.resources.forms import SearchResourceForm,OrgFilterForm
from apps.orgs.mixins import OrgMembershipRequiredMixin, TeacherRequiredMixin

class SearchResources(OrgMembershipRequiredMixin,TeacherRequiredMixin,LoginRequiredMixin,View):
    template_name = "resources/search_resources.html"
    search_resource_form_class=SearchResourceForm
    org_fitler_form_class = OrgFilterForm
    
    def get(self,request,*args,**kwargs):
        root,_ = self.get_root_current_org()
        search_resource_form = self.search_resource_form_class()
        org_fitler_form = self.org_fitler_form_class(root_org = root.id)
        context = {'search_resource_form':search_resource_form,'org_fitler_form':org_fitler_form}
        if request.htmx:
            return render(request,'resources/search_resources.html#search-resources',context)
        return render(request,self.template_name,context)


#     filters = {
#     "Year": "2024",
#     "Subject": "Java",
#     "Departments": "VSIT",
# }

# resources = Resource.objects.filter(snapshots__contains=[filters])