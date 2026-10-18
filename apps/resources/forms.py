from django import forms
from django.shortcuts import get_object_or_404
from apps.classes.models import Classroom
from apps.orgs.models import Organization
from apps.resources.models import Resource
from django.utils.translation import gettext_lazy as _

class SearchResourceForm(forms.ModelForm):
    title = forms.CharField(max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder':'search by title', 
        'class':"form-input w-full", 'autofocus': True }),
    )
    type = forms.ChoiceField(
        choices= Resource.ResourceType,
        widget=forms.CheckboxSelectMultiple(attrs={
        'class': 'bg-black'}),
    )
    class Meta:
        model = Resource
        fields = ['title','type']

class OrgFilterForm(forms.Form):
    def __init__(self,*args,**kwargs):

        root_org_id = kwargs.pop("root_org")
        super().__init__(*args, **kwargs)
        org = get_object_or_404(Organization.objects.select_related('config'),pk=root_org_id)
        template = org.config.template()
        nodes = Organization.objects.get_descendants(org).values_list('id','name')

        for depth, level_name in enumerate(template[:-1], start=2):
            # If not order_by, uses default Meta.ordering
            choices = nodes.filter(depth=depth).order_by("name").values_list("name", "name").distinct("name") # need distinct on "name" and PostgreSQL DISTINCT ON requires ORDER BY to start with the distinct field

            self.fields[level_name] = forms.MultipleChoiceField(
                choices=choices,
                required=False,
                label=level_name,
                widget=forms.SelectMultiple(attrs={
                    "class": "form-select w-full",
                }),
            )

        subjects = set()
        leaf_nodes = nodes.filter(depth = len(template))
        for node in leaf_nodes:
            # at classroom level they are already distinct, only make sure they are distinct across sub-orgs by using a set.
            node_classrooms = Classroom.objects.filter(parent_id = node[0] ).values_list('name','name') # returns a queryset iterable
            subjects.update(node_classrooms) # extend/update not append, they traverses the queryset and append tuples. append will directly append the queryset.

        self.fields[template[-1]] = forms.MultipleChoiceField(
            choices=sorted(subjects),
            required=False,
            label=template[-1],
            widget=forms.SelectMultiple(attrs={
                "class": "form-select w-full",
            }),
        )
