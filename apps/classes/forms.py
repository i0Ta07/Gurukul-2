from django import forms
from .models import Classroom,Announcement

class ClassroomNameForm(forms.ModelForm):
    name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'placeholder':'name', 
        'class':"form-input", 'autofocus': True })       
    )
    class Meta:
        model = Classroom
        fields = ['name']

class AnnouncementForm(forms.ModelForm):
    body = forms.CharField(
        max_length=300,
        required=True,
        widget=forms.Textarea(attrs={'placeholder':'Type here', 
        'class':"form-input", 'autofocus': True ,'rows':6})   
    )
    class Meta:
        model = Announcement
        fields = ['body']