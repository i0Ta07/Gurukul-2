from django.contrib import admin
from apps.classes.models import Classroom,ClassMembership,Announcement

# Register your models here.
admin.site.register(Classroom)
admin.site.register(ClassMembership)
admin.site.register(Announcement)