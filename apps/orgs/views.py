
from config.mixins import TeacherRequiredMixin
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render,get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.orgs.models import Organization,OrgMembership,OrgAdmin
from django.http import HttpResponseNotAllowed,HttpResponse,Http404
from apps.orgs.models import validate_child_org
from django.core.exceptions import ValidationError
from apps.orgs.forms import CreateOrgForm
from django.db.models import Exists,OuterRef
from apps.users.models import User
from enum import Enum
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

# def _build_breadcrumbs(node: Organization):
#     """
#     Returns:
#     [
#         {"name": "Harvard", "path": "/harvard"},
#         {"name": "CSE", "path": "/harvard/CSE"},
#         {"name": "2024", "path": "/harvard/CSE/2024"},
#     ]
#     get_ancestors returns from root. Therefore parts = [harvard] -> [harvard,CSE] -> [harvard,CSE,2024]
#     which then get appended with the ancestor
#     """
#     breadcrumbs = []
#     path = ""

#     for ancestor in node.get_ancestors():
#         path = f"{path}/{ancestor.slug}" if path else ancestor.slug
#         breadcrumbs.append(
#             {
#                 "name": ancestor.name,
#                 "path": path,
#             }
#         )

#     return breadcrumbs

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

def _build_path(node:Organization):
    parts = []
    for ancestor in node.get_ancestors():
        parts.append(ancestor.slug)

    path = "/".join(parts)
    return str(path)

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
            context = {"orgs": orgs,"is_root":True}
            if request.htmx:
                    return render(request, "orgs/list_orgs.html#view-org",context)
            return render(request, self.template_name, context)
        else:
            slugs = [slug for slug in org_path.strip("/").split("/") if slug]
            root_node = get_object_or_404(Organization.get_root_nodes().filter(), slug = slugs[0]) # Get root node
            role = _validate_root_access(root = root_node,user= request.user) # Check if user has access to root node
            if role:            
                current_node = _resolve_org_path(root_node =root_node,slugs=slugs)
                children = current_node.get_children().order_by("name")
                classes = current_node.classrooms.order_by('name')
                context = {
                    "role":role,
                    "orgs":_build_slug(children,org_path),
                    "classes":_build_slug(classes,org_path),
                    "current_org_name": current_node.name,
                    "current_org_id": current_node.id,
                    "current_org_path":org_path,
                    "breadcrumbs": _build_breadcrumbs(org_path), 
                    "can_add_child_org": not classes.exists(),
                    "can_add_class": not children.exists(),
                }
                if request.htmx:
                    return render(request, "orgs/list_orgs.html#view-org",context)
                    
                return render(request, self.template_name, context)
            return HttpResponse(status=401)


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
        return render(request, "orgs/list_orgs.html#org-row",row_context)



# build breadcrumb more efficiently
# @login_required
# def create_child_org(request, id, path):
#     if request.method != "POST":
#         return HttpResponseNotAllowed(["GET"])

#     parent = get_object_or_404(Organization, pk=parent_id)

#     # Load post data into the form
#     form = CreateOrgForm(request.POST)

#     if form.is_valid():
#         org = form.save(commit=False)
#         org.created_by = request.user
#         try:
#             validate_child_org(parent, org)
#             parent.add_child(instance=org)
#             path = _build_slug([org],parent_path)[0]['path']
#             context = {
#                 "org":{ "name":org.name,"path":path
#                 }
#             }
#             return render(request, "orgs/org_detail.html#org-row",context)
#         except ValidationError:
#             return HttpResponse(status=400)
#     return HttpResponse(status=400)




# Validate that the user is teacher and he is a member of the root org, then only he can access the org childs.
# Create a TeacherRequiedMixin in the config folder
# def org_detail(request, org_path:str):
    
    
#     print
#     try:
#         current_node = _resolve_org_path(org_path)
#     except Http404:
#         return create_message_and_redirect(request,f"Invalid Path",'users-dashboard')

#     child_orgs = (
#         current_node.get_children().order_by("name")
#     )

#     classes = (
#         current_node.classes.order_by("name")
#     )

#     # rule: org children and classes cannot coexist under the same node.
#     # So in practice one of these will be empty.
#     show_orgs = child_orgs.exists()
#     show_classes = not show_orgs

#     return render(
#         request,
#         "orgs/org_detail.html",
#         {
#             "current_node": current_node,
#             "breadcrumbs": _build_breadcrumbs(current_node),
#             "child_orgs": _build_slug(child_orgs,org_path),
#             "classes": _build_slug(classes,org_path),
#             "show_orgs": show_orgs,
#             "show_classes": show_classes,
#             "can_add_org": not classes.exists(),
#             "can_add_class": not child_orgs.exists(),
#         },
#     )