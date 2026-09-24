from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Define admin model for custom User model with no email field."""

    fieldsets = (
        (None, {'fields': ('username','email', 'password','user_type',)}),
        (_('Personal info'), {'fields': ('first_name', 'last_name','phone_number','date_of_birth','profile_photo','bio')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined','last_seen')}),
    )
    add_fieldsets = (
        (
            None, 
            {
                'classes': ('wide',),
                'fields': ('username','email', 'password1', 'password2','user_type'),
            }
        ),
    )
    list_display = ('email','username', 'first_name','user_type', 'is_staff')
    search_fields = ('username','email',)
    ordering = ('email','username',)

