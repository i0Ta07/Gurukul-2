from django import forms
from apps.quizzes.models import Quiz

class SearchQuizForm(forms.ModelForm):
    title = forms.CharField(max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder':'search by title', 
        'class':"form-input w-full", 'autofocus': True }),
    )
    class Meta:
        model = Quiz
        fields = ['title']
