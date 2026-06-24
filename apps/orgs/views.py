from django.shortcuts import render,get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Organization
from django.urls import reverse
from django.http import Http404
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

def org_index(request):
    roots = (
        Organization.get_root_nodes()
        .filter(is_active=True)
        .order_by("name")
    )
    

    return render(
        request,
        "orgs/org_index.html",
        {
            "roots": roots,
        },
    )

def build_child_orgs(child_orgs, parent_path):
    return [
        {
            "name": child.name,
            "path": f"{parent_path}/{child.slug}", # org_path always vips/vsit not vips/vsit/
        }
        for child in child_orgs
    ]

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
            "child_orgs": build_child_orgs(child_orgs,org_path),
            "classes": classes,
            "show_orgs": show_orgs,
            "show_classes": show_classes,
            "can_add_org": not classes.exists(),
            "can_add_class": not child_orgs.exists(),
        },
    )