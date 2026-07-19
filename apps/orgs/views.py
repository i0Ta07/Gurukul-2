
from config.mixins import TeacherRequiredMixin
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render,get_object_or_404
from apps.orgs.models import Organization,OrgMembership,OrgAdmin
from apps.orgs.models import validate_child_org,validate_root_org
from django.core.exceptions import ValidationError
from apps.orgs.forms import CreateOrgForm,CreateRootOrgForm,CreateOrgConfig
from django.db.models import Exists,OuterRef
from apps.users.models import User
from enum import Enum
from django.db import transaction
from config.utils import create_message_and_redirect
# Create your views here.
# Call add_root()
# filter returns a querySet


# OMG,this function is pure beauty.
def _resolve_org_path(root_node: Organization, slugs) -> Organization:
    """
    Resolve a slug path like: harvard/cse/2024 into the matching Organization node.
    It resolves the URL, level by level. First it retrieves the root node at slugs[0] -> harvard among all root nodes.
    Then it goes folder by folder matching the path. If current = harvard.get_childern() has cse then current = cse
    then current = cse.get_children() has 2024 then current = 2024. We got the last node. 
    
    Suppose we have two paths like harvard/cse/2024 and harvard/mechanical/2024. Since , it goes folder by, it reaches
    the exact path. If suppose we have harvard/biochem and it does not exist, it will return HTTP404 since current.get_children(), slug = slug
    does not have biochem 
    """

    current = root_node
    for slug in slugs[1:]:
        current = get_object_or_404(current.get_children(), slug=slug)

    return current

def _build_breadcrumbs(org_path: str):
    breadcrumbs = []
    current_path = ""

    for slug in org_path.strip("/").split("/")[0:-1]:
        current_path += f"/{slug}"
        breadcrumbs.append({
            "name": slug.upper(),
            "path": current_path,
        })

    return breadcrumbs

def _build_slug(objects,parent_path = ""):
    """
    Build paths for a list of objects, based on parent_path. 
    Adds the current object slug at the end of parent path.
    Can work with both child orgs and classes.
    """
    return [
        {
            "name": obj.name,
            "path": f"{parent_path}/{obj.slug}" if parent_path else f"{obj.slug}", # org_path always vips/vsit not vips/vsit/
        }
        for obj in objects
    ]


class UserRole(str, Enum):
    OWNER = "Owner"
    ADMIN = "Admin"
    TEACHER = "Teacher"

def _validate_root_access(root:Organization,user:User):
    """
    Check if the user belong to this root org, it yes return the role [Admin,Teacher,Owner] else return None
    """
    if Organization.get_root_nodes().filter(id = root.id, config__owner = user).exists():
        return UserRole.OWNER.value
    membership = (
        OrgMembership.objects.filter(org=root, teacher=user).annotate(
            has_admin=Exists(
                OrgAdmin.objects.filter(membership=OuterRef("id"))
            )
        ).first()
    )
    if membership:
        return UserRole.ADMIN.value if membership.has_admin else UserRole.TEACHER.value
    return None

    
# should only show the TLD orgs the user has created
class ViewOrgs(LoginRequiredMixin, TeacherRequiredMixin, View):
    template_name = "orgs/list_orgs.html"
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        org_path = kwargs.get("org_path")
        if not org_path: # If there is no org_path that means that we are at / and extract the created and membership orgs for the user.
            created_orgs = Organization.get_root_nodes().filter(config__owner = request.user)
            memberships = (
                OrgMembership.objects.filter(teacher=request.user).select_related("org").annotate(
                    has_admin=Exists(
                        OrgAdmin.objects.filter(membership=OuterRef("id")) # whether this membership.id exists in OrgAdmin membership field
                    )
                )
            )

            orgs = [
                *(
                    {
                        "name": org.name,
                        "path": f"{org.slug}",
                        "role": UserRole.OWNER.value,
                    }
                    for org in created_orgs
                ),
                *(
                    {
                        "name": membership.org.name,
                        "path": f"{membership.org.slug}",
                        "role": UserRole.ADMIN.value if membership.has_admin else UserRole.TEACHER.value,
                    }
                    for membership in memberships
                ),
            ]
            context = {"orgs": orgs,"root_org_view":True}
            if request.htmx:
                    return render(request, "orgs/list_orgs.html#view-org",context)
            return render(request, self.template_name, context)
        else:
            slugs = [slug for slug in org_path.strip("/").split("/") if slug]
            root_node = get_object_or_404(Organization.get_root_nodes().filter(), slug = slugs[0]) # Get root node
            org_role = _validate_root_access(root = root_node,user= request.user) # Check if user has access to root node
            if org_role:            
                current_node = _resolve_org_path(root_node =root_node,slugs=slugs)
                children = current_node.get_children().order_by("name")
                template = root_node.config.template()
                current_depth = current_node.get_depth()
                if template:
                    node_label = template[current_depth -1]
                else:
                    node_label = "Organization"
                classes = current_node.classrooms.order_by('name')
                context = {
                    "org_role":org_role,
                    "orgs":_build_slug(children,org_path),
                    "classes":_build_slug(classes,org_path),
                    "current_org_name": current_node.name,
                    "current_org_id": current_node.id,
                    "current_org_path":org_path,
                    "breadcrumbs": _build_breadcrumbs(org_path), 
                    "child_org_view": not classes.exists() and current_depth != len(template),
                    "class_view": not children.exists()  and current_depth  == len(template),
                    "node_label":node_label,
                }
                if request.htmx:
                    return render(request, "orgs/list_orgs.html#view-org",context)
                    
                return render(request, self.template_name, context)
            return create_message_and_redirect(request,message="You are not part of this organization",url="users-dashboard",code="error")


class CreateChildOrg(LoginRequiredMixin,TeacherRequiredMixin,View):
    template_name = "orgs/partials/create_child_org.html"
    form_class = CreateOrgForm

    def get(self,request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form":form,"org_id":kwargs['org_id'],"org_path":kwargs['org_path']})

    
    def post(self, request, *args, **kwargs):
        parent_id = kwargs['org_id']
        parent_path = kwargs['org_path']

        parent = get_object_or_404(Organization, pk=parent_id)

        # Load post data into the form
        form = self.form_class(request.POST)
        form_context = {"form":form,"org_id":kwargs['org_id'],"org_path":kwargs['org_path']}
        if not form.is_valid():
            return render(request, self.template_name,form_context)
        org = form.save(commit=False)
        org.created_by = request.user
        try:
            validate_child_org(parent_node = parent, instance=org)
        except ValidationError as e:
            form.add_error(field=None,error=e.message)
            return render(request, self.template_name,form_context)
        parent.add_child(instance=org)
        path = f"{parent_path}/{org.slug}" if parent_path else org.slug
        row_context = {
            "org":{ "name":org.name,"path":path}
        }
        messages.success(request,message="Organization created successfully.")
        response = render(request, "orgs/list_orgs.html#org-row",row_context)
        response['HX-Trigger'] = 'child-org-created'
        return response

class CreateRootOrgAndConfig(LoginRequiredMixin,TeacherRequiredMixin,View):
    template_name = "orgs/partials/create_root_and_config_org.html"
    root_form = CreateRootOrgForm
    config_form = CreateOrgConfig

    def get(self,request, *args, **kwargs):
        root_form = self.root_form()
        config_form = self.config_form()
        return render(request, self.template_name, {"root_form":root_form,"config_form":config_form})
    
    def post(self, request, *args, **kwargs):
        def render_error():
            response = render(
                request,
                self.template_name,
                {
                    "root_form": root_form,
                    "config_form": config_form,
                },
            )
            response["HX-Retarget"] = "#modal_container" # Change the target to inside modal from main-list if there is an error
            response["HX-Reswap"] = "innerHTML" # Change the swap method to innerHTML from afterbegin inside the target container
            return response

        root_form = self.root_form(request.POST)
        config_form = self.config_form(request.POST)

        if not root_form.is_valid() or not config_form.is_valid():
            return render_error()
        
        org = root_form.save(commit=False)
        org.created_by = request.user

        try:
            validate_root_org(instance=org)
        except ValidationError as e:
            root_form.add_error(field=None,error=e.message)
            return render_error()
        
        org_config = config_form.save(commit=False)
        org_config.org = org
        org_config.owner = request.user

        with transaction.atomic(): # either both root and config are created or none
            Organization.add_root(instance = org)
            org_config.save()

        messages.success(request,"Organization created successfully")
        response = render(request,"orgs/list_orgs.html#org-row", {
            "org":{"name":org.name, "path":f"{org.slug}","role":UserRole.OWNER.value},
            "root_org_view":True,
            }
        )
        response['HX-Trigger'] = 'root-org-created'
        return response