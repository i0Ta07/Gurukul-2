from os import name

from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from .models import Organization
from django.http import Http404
from django.http import HttpResponseNotAllowed,HttpResponse
from .models import _validate_org_structure,Class
from django.core.exceptions import ValidationError
from .forms import CreateClassForm,CreateOrgForm
from django.contrib import messages
from django.views import View
# Create your views here.
# Call add_root()


# OMG,this function is pure beauty.
def resolve_org_path(org_path: str) -> Organization:
    """
    Resolve a slug path like: harvard/cse/2024 into the matching Organization node.
    It resolves the URL, level by level. First it retrieves the root node at slugs[0] -> harvard among all root nodes.
    Then it goes folder by folder matching the path. If current = harvard.get_childern() has cse then current = cse
    then current = cse.get_children() has 2024 then current = 2024. We got the last node. 
    
    Suppose we have two paths like harvard/cse/2024 and harvard/mechanical/2024. Since , it goes folder by, it reaches
    the exact path. If suppose we have harvard/biochem and it does not exist, it will return HTTP404 since current.get_children(), slug = slug
    does not have biochem 
    """
    slugs = [slug for slug in org_path.strip("/").split("/") if slug]
    if not slugs:
        raise Http404("Organization not found.")

    current = get_object_or_404(Organization.get_root_nodes(), slug=slugs[0])

    for slug in slugs[1:]:
        current = get_object_or_404(current.get_children(), slug=slug)

    return current


def build_breadcrumbs(node: Organization):
    """
    Returns:
    [
        {"name": "Harvard", "path": "/harvard"},
        {"name": "CSE", "path": "/harvard/CSE"},
        {"name": "2024", "path": "/harvard/CSE/2024"},
    ]
    get_ancestors returns from root. Therefore parts = [harvard] -> [harvard,CSE] -> [harvard,CSE,2024]
    which then get appended with the ancestor
    """
    breadcrumbs = []
    parts = []

    for ancestor in node.get_ancestors():
        parts.append(ancestor.slug)
        breadcrumbs.append(
            {
                "name": ancestor.name,
                "path": "/".join(parts),
            }
        )
    return breadcrumbs

def build_path(node:Organization):
    parts = []
    for ancestor in node.get_ancestors():
        parts.append(ancestor.name)

    path = "/".join(parts)
    return str(path)

def build_slug(objects,parent_path = ""):
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

# should only show the TDS orgs the user has created
@login_required
def org_index(request):
    roots = (
        Organization.get_root_nodes()
        .filter(is_active=True)
        .order_by("name")
    )
    print(roots)
    
    return render(
        request,
        "orgs/org_index.html",
        {
            "roots": build_slug(roots),
        },
    )

@login_required
def create_classroom(request, org_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    org = get_object_or_404(Organization, pk=org_id)

    form = CreateClassForm(request.POST)

    if form.is_valid():
        classroom = form.save(commit=False)
        classroom.org = org
        classroom.created_by = request.user

        try:
            classroom.save()
            messages.success(request, "Classroom created successfully.")
        except ValidationError as e:
            messages.error(request, e.message)

    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    return redirect("org-detail", org_path=org.path)

@login_required
def create_org(request, org_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    parent = get_object_or_404(Organization, pk=org_id)

    # Load post date into the form
    form = CreateOrgForm(request.POST)

    if form.is_valid():
        name = form.cleaned_data.get("name")
        if not name.isalnum():
            return HttpResponse(status=400)
        org = form.save(commit=False)
        org.created_by = request.user
        try:
            _validate_org_structure(parent, org)
            parent.add_child(instance=org)
            path = build_path(org)
            context = {
                "org":{ "name":org.name,"path":path
                }
            }
            return render(request, "orgs/org_detail.html#org-row",context)
        except ValidationError:
            return HttpResponse(status=400)
    return HttpResponse(status=400)



def org_detail(request, org_path):
    current_node = resolve_org_path(org_path)
    child_orgs = (
        current_node.get_children()
        .filter(is_active=True)
        .order_by("name")
    )

    classes = (
        current_node.classes
        .filter(is_active=True)
        .order_by("name")
    )

    # Your rule: org children and classes cannot coexist under the same node.
    # So in practice one of these will be empty.
    show_orgs = child_orgs.exists()
    show_classes = not show_orgs

    return render(
        request,
        "orgs/org_detail.html",
        {
            "current_node": current_node,
            "breadcrumbs": build_breadcrumbs(current_node),
            "child_orgs": build_slug(child_orgs,org_path),
            "classes": build_slug(classes,org_path),
            "show_orgs": show_orgs,
            "show_classes": show_classes,
            "can_add_org": not classes.exists(),
            "can_add_class": not child_orgs.exists(),
        },
    )