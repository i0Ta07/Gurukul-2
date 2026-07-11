
from django import forms
# from django.contrib.auth.models import User
from .models import User
from django.contrib.auth.forms import UserCreationForm
from phonenumber_field.formfields import SplitPhoneNumberField
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import AuthenticationForm



class LoginForm(AuthenticationForm):
    # Django AuthenticationForm still requires the name as username but since we did USERNAME_FIELD = "email", it will get replace
    username = forms.EmailField(max_length=100,label=_('Email') ,required=True,widget=forms.EmailInput(attrs={
        'placeholder': 'john_doe@gmail.com',
        'class': 'form-input '
        })
    )
    
    password = forms.CharField(max_length=50,label=_('Password'),required=True,widget=forms.PasswordInput(attrs={
        'placeholder': '••••••••',
        'class': "form-input ",
        ':type': "showPass ? 'text': 'password'"
        })
    )
    remember_me = forms.BooleanField(required=False, label=_('Remember Me'), widget=forms.CheckboxInput(attrs={
        'class':'scheme-dark'
    } ))
    class Meta:
        model = User
        fields = ['username', 'password', 'remember_me']


class RegisterEmailForm(forms.Form):
    email = forms.EmailField(
        required=True,
        label=_('Email'),
        widget=forms.EmailInput(attrs={'placeholder': 'john_doe@gmail.com',
        'class':'form-input'}),
    )


class CompleteRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        label=_('Email'),
        disabled=True,
        widget=forms.EmailInput(attrs={'placeholder': 'john_doe@gmail.com',
        'class':'form-input'}),
    )

    first_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('First Name'),
        widget=forms.TextInput(attrs={'placeholder':'John', 
        'class':'form-input'}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('Last Name'),
        widget=forms.TextInput(attrs={'placeholder':'Snow', 
        'class': 'form-input'}),
    )
    user_type = forms.ChoiceField(
        choices=User.UserType,
        label=_('User Type'),
        required=True,
        # initial=User.UserType.STUDENT,
        widget=forms.Select(attrs={'class': ' form-input'}),
    )

    password1 = forms.CharField(max_length=20,
        label=_('Password'),
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder':'••••••••',
            ':type': "showPass ? 'text': 'password'"
            })
        )
    
    password2 = forms.CharField(
        label=_('Confirm Password'),
        max_length=20,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder':'••••••••',
            ':type': "showPass ? 'text': 'password'"
            })
        )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name','user_type',
            'password1', 'password2',
        ]

class BootstrapSplitPhoneNumberField(SplitPhoneNumberField):
    def prefix_field(self):
        field = super().prefix_field()
        field.widget.attrs.update({
            'class': 'form-input ',
        })
        return field

    def number_field(self):
        field = super().number_field()
        field.widget.attrs.update({
            "maxlength": 10,
            'class': 'form-input ',
            'placeholder': '10 digit number',
        })
        return field
    

class UpdateUserDetailsForm(forms.ModelForm):
    
    # We are using self.form_class(instance=request.user), if user has None then it will show None
    # to overide it, override form's __init__ to change values during instantiation.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.phone_number:
            self.initial["phone_number"] = ["IN", None]

    first_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('First Name'),
        widget=forms.TextInput(attrs={
        'class':'form-input'}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('Last Name'),
        widget=forms.TextInput(attrs={'placeholder':'Snow',
        'class': 'form-input'}),
    )
    email = forms.EmailField(
        required=True,
        label=_('Email'),
        widget=forms.EmailInput(attrs={
        'class': 'form-input '
        })
    )
    user_type = forms.ChoiceField(
        choices=User.UserType,
        label=_('User Type'),
        required=True,
        disabled=True,
        widget=forms.Select(attrs={
        'class': 'form-input'}),
    )


    phone_number = BootstrapSplitPhoneNumberField(
        label=_('Phone'),
        required=False,
    )
    date_of_birth = forms.DateField(
        label=_('Date of Birth'),
        widget=forms.DateInput(attrs={ 'type': 'date', # mention type date default string.
        'class': 'scheme-dark form-input'}),
        required=False
    )
    profile_photo = forms.ImageField(widget=forms.FileInput(attrs={'class': 
    "cursor-pointer text-sm text-gray-200 p-1 rounded-2xl border border-neutral-700 file:bg-slate-600  hover:file:bg-slate-800 file:rounded-2xl file:text-white file:mr-4 file:px-2 file:py-1 file:font-semibold "
    }),required=False)

    bio = forms.CharField(max_length=100,strip=True,label=_('Bio'),required=False,widget=forms.Textarea(attrs={'placeholder':'About you',
    'class': 'form-input h-25'}))

    # BootstrapSplitPhoneNumberField store '' instead of Null. So, predefined clean function for devs by django, called automatically.
    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        if not phone:
            return None
        return phone
    
    class Meta:
        model = User
        fields = ['first_name','last_name','email','user_type','phone_number','date_of_birth','profile_photo','bio']


