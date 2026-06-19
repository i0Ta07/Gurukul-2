from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User,Friendship

admin.register(User)
@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Define admin model for custom User model with no email field."""

    fieldsets = (
        (None, {'fields': ('email', 'password','user_type','is_verified')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name','phone_number','date_of_birth','profile_photo','bio')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None, 
            {
                'classes': ('wide',),
                'fields': ('email', 'password1', 'password2','user_type'),
            }
        ),
    )
    list_display = ('email', 'first_name','user_type', 'is_staff')
    search_fields = ('email',)
    ordering = ('email',)

admin.site.register(Friendship)