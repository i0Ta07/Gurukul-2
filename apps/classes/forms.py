from django import forms
from .models import Class

class CreateClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name']