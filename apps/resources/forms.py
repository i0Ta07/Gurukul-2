from django import forms
from django.shortcuts import get_object_or_404
from apps.classes.models import Classroom
from apps.orgs.models import Organization
from apps.resources.models import Resource
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from apps.resources.utils import clean_file_size
from config.validators import pdf_validator

class ResourceForm(forms.ModelForm):
    title = forms.CharField(max_length=100,
        widget=forms.TextInput(attrs={'placeholder':'Title', 
        'class':"form-input w-full", 'autofocus': True }),
    )
    type = forms.ChoiceField(
        choices=[('', 'Select type')] + Resource.ResourceType.choices, # .choices returns a list
        widget=forms.Select(attrs={
            'class': 'form-select w-full bg-black border border-gray-700 p-2 rounded-b-xl',
        }),
    )
    url = forms.URLField(
        max_length=200,
        required=False,
        widget=forms.URLInput(attrs={
            'placeholder':'Enter full URL',
            'class':'form-input w-full'
        })
    )
    file = forms.FileField(
        required=False,
        validators=[pdf_validator],
        label=_("Accepts PDFs smaller than 5 Megabytes."),
        widget=forms.FileInput(attrs={
            'class':'file-input w-full'
        })

    )
    class Meta:
        model=Resource
        fields = ['title', 'type', 'url', 'file']

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            clean_file_size(file,max_size=5)
        return file

    def clean(self):
        cleaned_data = super().clean()

        url = cleaned_data.get('url')
        file = cleaned_data.get('file')

        if bool(url) == bool(file): # either one of those
            raise ValidationError(
                'Provide either a URL or a file.'
            )

        return cleaned_data


class SearchResourceForm(forms.Form):
    title = forms.CharField(max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder':'search by title', 
        'class':"form-input w-full", 'autofocus': True }),
    )
    type = forms.MultipleChoiceField(
        required=False,
        choices= Resource.ResourceType,
        widget=forms.CheckboxSelectMultiple(),
    )

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
            self.fields[level_name] = forms.ChoiceField(
                choices= (("", f"{level_name}"),) + tuple(choices), # choice needs tuple of (id,name)
                required=False,
                label=level_name,
                widget=forms.Select(attrs={
                    "class": "form-select w-full bg-black border border-gray-700 p-2 rounded-b-xl",
                }),
            )

        subjects = set()
        leaf_nodes = nodes.filter(depth = len(template))
        for node in leaf_nodes:
            # at classroom level they are already distinct, only make sure they are distinct across sub-orgs by using a set.
            node_classrooms = Classroom.objects.filter(parent_id = node[0] ).values_list('name','name') # returns a queryset iterable
            subjects.update(node_classrooms) # extend/update not append, they traverses the queryset and append tuples. append will directly append the queryset.

        self.fields[template[-1]] = forms.ChoiceField(
            choices=(("", "Subjects"),) + tuple(subjects),
            required=False,
            label=template[-1],
            widget=forms.Select(attrs={
                "class": "form-select w-full bg-black border border-gray-700 p-2 rounded-b-xl",
            }),
        )