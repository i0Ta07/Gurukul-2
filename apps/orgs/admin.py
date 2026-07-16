from django.contrib import admin

from .models import OrgConfig, Organization,OrgAdmin,OrgMembership

# Register your models here.
admin.site.register(Organization)
admin.site.register(OrgMembership)
admin.site.register(OrgAdmin)
admin.site.register(OrgConfig)