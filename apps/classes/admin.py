from django.contrib import admin
from apps.classes.models import Class,ClassMembership

# Register your models here.
admin.site.register(Class)
admin.site.register(ClassMembership)