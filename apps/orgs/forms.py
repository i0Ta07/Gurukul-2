from django import forms
from .models import Class,validate_org_structure,Organization
from treebeard.forms import MoveNodeForm, movenodeform_factory
from django.http import HttpResponse


class CreateClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name']

class CreateOrgForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name']
        

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
        

        validate_org_structure(
            instance=self.instance, 
            ref_node=target_node, 
            position=position
        )
            
        return cleaned_data

# Generate the actual form class using the factory
OrganizationForm = movenodeform_factory(
    Organization,
    form=MoveOrganizationForm,
    exclude=[ 'is_active','created_at','created_by'] # handle these along with .move in views.
)