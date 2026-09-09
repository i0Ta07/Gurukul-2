from django import forms
from .models import Classroom

class ClassroomNameForm(forms.ModelForm):
    name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'placeholder':'name', 
        'class':"form-input",
        "placeholder": 'name', 'autofocus': True })       
    )
    class Meta:
        model = Classroom
        fields = ['name']
