from django import forms
from .models import OrgConfig, Organization
from django.utils.translation import gettext_lazy as _

from .models import validate_child_org
from treebeard.forms import MoveNodeForm, movenodeform_factory

class CreateOrgForm(forms.ModelForm):
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

class CreateOrgConfig(forms.ModelForm):
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