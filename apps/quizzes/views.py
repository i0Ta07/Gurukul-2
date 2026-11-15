from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View
from apps.orgs.mixins import OrgMembershipRequiredMixin, TeacherRequiredMixin
from apps.quizzes.forms import SearchQuizForm
from apps.resources.forms import OrgFilterForm

# Create your views here.

class SearchQuizzesView(LoginRequiredMixin,TeacherRequiredMixin, OrgMembershipRequiredMixin,View):
    template_name = "quizzes/search_quizzes.html"
    template_partial_name = "quizzes/search_quizzes.html#search-quizzes"
    search_quiz_form_class=SearchQuizForm
    org_fitler_form_class = OrgFilterForm

    def get(self,request,*args,**kwargs):
        root,_ = self.get_root_current_org()
        search_quiz_form = self.search_quiz_form_class()
        org_fitler_form = self.org_fitler_form_class(root_org = root.id)
        context = {'search_quiz_form':search_quiz_form,'org_fitler_form':org_fitler_form,'org_id':root.id,'org_name':root.name}
        if request.htmx:
            return render(request,self.template_partial_name,context)
        return render(request,self.template_name,context)

