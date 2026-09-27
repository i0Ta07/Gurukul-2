from django import forms
from apps.chats.models import RoomMessage, ThreadMessage

class ThreadMessageForm(forms.ModelForm):
    body = forms.CharField(
        max_length=300,
        required=True,
        widget= forms.TextInput(
            attrs={
                'class':'form-input mt-1 h-13',
                'placeholder':'Type your message'
            }
        )
    )

    class Meta:
        model = ThreadMessage
        fields = ['body']

class RoomMessageForm(forms.ModelForm):
    body = forms.CharField(
        max_length=300,
        required=True,
        widget= forms.TextInput(
            attrs={
                'class':'form-input mt-1 h-13',
                'placeholder':'Type your message'
            }
        )
    )
    
    class Meta:
        model = RoomMessage
        fields = ['body']

class SearchUserForm(forms.Form):
    username = forms.CharField(max_length=150 ,required=True,widget=forms.TextInput(attrs={
        'placeholder': 'Search for users by username',
        'class': 'form-input h-13'
        })
    )