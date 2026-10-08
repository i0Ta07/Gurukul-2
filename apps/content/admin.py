from django.contrib import admin
from apps.content.models import Resource,ResourceClassMembership

# Register your models here.
admin.site.register(Resource)
admin.site.register(ResourceClassMembership)