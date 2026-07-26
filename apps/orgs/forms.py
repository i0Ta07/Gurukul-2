from django import forms
from .models import  OrgConfig, Organization, OrgMembership
from django.utils.translation import gettext_lazy as _
from apps.orgs.utils import validate_child_org
from treebeard.forms import MoveNodeForm, movenodeform_factory
from django.template.defaultfilters import filesizeformat
from django.core.exceptions import ValidationError
from config.validators import validate_file_mimetype
from django.forms import ModelChoiceField

class CreateChildOrgForm(forms.ModelForm):
    name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'placeholder':'name', 
        'class':"form-input w-25",
        "placeholder": 'name', 'autofocus': True })       
    )
    class Meta:
        model = Organization
        fields = ['name']

class CreateRootOrgForm(forms.ModelForm):
    name = forms.CharField(
        max_length=50,
        label=_('Name'),
        required=True,
        widget=forms.TextInput(attrs={
        'class':"form-input",
        "placeholder": 'Must be unique', 'autofocus': True })       
    )
    class Meta:
        model = Organization
        fields = ['name']

class CreateOrgConfigForm(forms.ModelForm):
    type = forms.ChoiceField(
        choices= OrgConfig.OrganizationType,
        label=_("Type"),
        required=True,
        widget=forms.RadioSelect(attrs={
        'class': ' outline-none'}),
    )
    class Meta:
        model = OrgConfig
        fields = ['type']

class SendInvitationForm(forms.Form):

    email = forms.EmailField(
        required=False,
        label=_('Email'),
        widget=forms.EmailInput(attrs={'placeholder': 'john_doe@gmail.com', 'class':'form-input w-72 md:w-lg'}),
    )

    file = forms.FileField(
        required=False,
        label=_('Import from excel file (.xlsx). Size: 2MB'),
        widget=forms.FileInput(attrs={'class':"file-input"}),
        validators=[validate_file_mimetype(allowed_mime_types=['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'])]
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            max_size = 2097152 # 2 MB limit (2 * 1024 * 1024 bytes)
            if file.size > max_size:
                raise ValidationError(
                    f"File too large. Size must be under {filesizeformat(max_size)}."
                    f"Current size is {filesizeformat(file.size)}."
                )
        return file
    
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get("file")
        email = cleaned_data.get("email")

        if not file and not email:
            raise ValidationError("Both fields cannot be empty.")
        
class MembershipModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.teacher.first_name} {obj.teacher.last_name} ({obj.teacher.email})"
    
class CreateAdminForm(forms.Form):
    users = MembershipModelChoiceField(
        empty_label="Select user",
        queryset=OrgMembership.objects.none(),
        widget=forms.Select(attrs={'class': ' form-input'}),
    )

    def __init__(self, *args, **kwargs):
        root_org = kwargs.pop("root_org")
        super().__init__(*args, **kwargs)
        self.fields["users"].queryset = (
            OrgMembership.objects
            .filter(org=root_org)
            .filter(admin__isnull=True)
        )

# Create a get org form that will take a org slug, then check among the root_nodes check if that org
# exists if yes, then check the membership of the user to the org.

class MoveOrganizationForm(MoveNodeForm):
    """
    Overrides the default Treebeard MoveNodeForm to hook our custom validation
    engine into the Django Form lifecycle.
    """
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Extract the modern Treebeard fields directly from the submitted form data
        target_node = cleaned_data.get('treebeard_ref_node')
        position = cleaned_data.get('treebeard_position') # either sorted-child or sorted-sibling
        

        validate_child_org(
            instance=self.instance, 
            ref_node=target_node, 
            position=position
        )
            
        return cleaned_data

# Generate the actual form class using the factory
OrganizationForm = movenodeform_factory(
    Organization,
    form=MoveOrganizationForm,
    # Add pos to it since we are only adding/moving child
    exclude=[ 'is_active','created_at','created_by'] # handle these along with .move in views. 
)