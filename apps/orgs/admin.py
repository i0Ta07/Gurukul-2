from django.contrib import admin

from .models import Class, ClassMembership, Organization

# Register your models here.
admin.site.register(Organization)
admin.site.register(Class)
admin.site.register(ClassMembership)