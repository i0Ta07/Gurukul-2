from django import forms
from .models import Class,_validate_org_structure,Organization
from treebeard.forms import MoveNodeForm, movenodeform_factory


class CreateClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name', 'org']


class BaseOrganizationForm(MoveNodeForm):
    """
    Overrides the default Treebeard MoveNodeForm to hook our custom validation
    engine into the Django Form lifecycle.
    """
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Extract the modern Treebeard fields directly from the submitted form data
        target_node = cleaned_data.get('treebeard_ref_node')
        position = cleaned_data.get('treebeard_position') # either sorted-child or sorted-sibling
        

        _validate_org_structure(
            instance=self.instance, 
            target_node=target_node, 
            position=position
        )
            
        return cleaned_data

# Generate the actual form class using the factory
OrganizationForm = movenodeform_factory(
    Organization,
    form=BaseOrganizationForm,
    exclude=[ 'is_active','created_at','created_by'] # handle these along with .move in views.
)