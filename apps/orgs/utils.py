from apps.classes.models import Classroom
from apps.orgs.models import Organization,OrgMembership,OrgAdmin
from apps.users.models import User
from django.db.models import Exists,OuterRef
from enum import Enum
from config.settings import MAX_DEPTH
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.shortcuts import get_object_or_404
from openpyxl import load_workbook
from django.core.validators import EmailValidator
from collections.abc import Iterable
from django.db.models.query import QuerySet
import secrets

class UserRole(str, Enum):
    OWNER = "Owner"
    ADMIN = "Admin"
    TEACHER = "Teacher"

def get_user_role(root:Organization,user:User):
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

def is_owner_or_admin(root:Organization,user:User):
    role = get_user_role(root=root,user=user)
    if role in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        return True
    return False

def is_owner(root:Organization,user:User):
    role = get_user_role(root=root,user=user)
    if role == UserRole.OWNER.value:
        return True
    return False

# in the root node we only have to validate the uniques sibling for else we have to additonally check if height < MAX_HEIGHT and classrooms exists
# also we are always adding child node, not sibling. When move we will move inside a org as a child not a sibling.
# node.move(ref_node= node1, pos="sorted-child")

def validate_root_org(instance:Organization):
        """Validate root org, check if the siblings are unique."""
        _validate_unique_siblings(instance = instance)

def validate_child_org(parent_node: Organization, instance: Organization):
    """
    parent_node: we can only move and create inside a org as a child, not a sibling.
    instance: when move -> existing_node; when create: new_node
    position: always child.
    Can be used with create root/child orgs and move child orgs.
    """

    target_depth = parent_node.depth + 1

    # --- RULE 1: Maximum Depth Limit ---
    
    _validate_depth(target_depth = target_depth,instance = instance)


    # ---RULE 2: Classes at leaf nodes ---
    
    if parent_node.classrooms.exists():
        raise ValidationError(f'Organization and classrooms cannot be in same folder.')

    # --- RULE 3: Scoped Sibling Uniqueness &  ---
    _validate_unique_siblings(parent_node = parent_node,instance= instance)

# p1.add_sibling(pos = "sibling",p2)

def _validate_depth(target_depth:int, instance:Organization):
    """
    Validate the depth of the instance, given it's expected depth i.e. target depth and instance itself.
    Handle both create and move.
    """
    # New Node Creation Validation 
    if not instance.pk:
        if target_depth > MAX_DEPTH:
            raise ValidationError(f"Nesting limit exceeded! Maximum allowed depth is {MAX_DEPTH}. This would be level {target_depth}.")
    else:
    # Moving an existing node (must account for the height of its children)
        descendants = instance.get_descendants()
        if descendants.exists():
            max_descendant_depth = descendants.order_by('-depth').first().depth
            subtree_height = max_descendant_depth - instance.depth
        else:
            subtree_height = 0

        if (target_depth + subtree_height) > MAX_DEPTH:
            raise ValidationError(f"Cannot move here. This branch is {subtree_height + 1} levels tall, which would push nested organizations past the {MAX_DEPTH}-level limit.")

def _validate_unique_siblings(instance:Organization, parent_node:Organization = None ):
    """
    Validate that siblings have unique name either during move or new node creation.
    For root orgs, we only provide the instance.
    """
    if parent_node:
        siblings = parent_node.get_children()
    else:
        siblings = Organization.get_root_nodes()
   
    # When moving, siblings also contains the current node, so exclude that.
    if instance.pk:
        siblings = siblings.exclude(pk=instance.pk)

    slug = slugify(instance.name)

    if siblings.filter(slug=slug).exists():
        raise ValidationError(f"The root name must be unique.")
           
# OMG,this function is pure beauty.
def resolve_org_path(root_node: Organization, slugs) -> Organization:
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

def build_breadcrumbs(org_path: str):
    """
    Build breadcrumb navigation for an organization path.

    Returns a list of dictionaries containing the display name and cumulative path
    for each organization level, excluding the final segment.
    """
    breadcrumbs = []
    current_path = ""

    for slug in org_path.strip("/").split("/")[0:-1]:
        current_path += f"/{slug}"
        breadcrumbs.append({
            "name": slug.upper(),
            "path": current_path,
        })

    return breadcrumbs

def _serialize_many(instance, serializer):
    if isinstance(instance, Iterable) and not isinstance(instance, (str, bytes)):
        return [serializer(obj) for obj in instance]
    return serializer(instance)

def build_slug(instance: Organization| Iterable[Organization] | Classroom | Iterable[Classroom],
        parent_path:str = "",role: UserRole | None = None):
    """
    Pass role when displaying root orgs only. This can work with both child orgs and classrooms.
    """
    def serialize(obj):
        data = {
            "name":obj.name,
            "id":obj.id,
            "path": f"{parent_path}/{obj.slug}" if parent_path else obj.slug,
        }

        if role is not None:
            data["role"] = role.value
        return data
    
    return _serialize_many(instance,serialize)

def build_membership_slug(instance: OrgMembership | Iterable[OrgMembership]):
    def serialize(membership):
        data = {
            "name": membership.org.name,
            "path": f"{membership.org.slug}",
            "role": UserRole.ADMIN.value if membership.has_admin else UserRole.TEACHER.value,
            "id":membership.org.id,
        }
        return data

    return _serialize_many(instance,serialize)

def annotate_memberships(queryset: QuerySet[OrgMembership]):
    """Annotate has_admin attribute to each OrgMembership object in the queryset."""
    return queryset.annotate(
            has_admin=Exists(
                OrgAdmin.objects.filter(membership=OuterRef("id")) # whether this membership.id exists in OrgAdmin membership field
                )
            )

def get_emails_from_excel(file):
    workbook = load_workbook(file, read_only=True, data_only=True)
    worksheet = workbook.active

    email_validator = EmailValidator()

    HEADER_NAMES = {"email","e-mail","email address","email id","mail",}
    MAX_EMAILS = 100

    emails = set()

    def add_email(value):
        if not isinstance(value, str):
            return

        value = value.strip()

        try:
            email_validator(value)
        except ValidationError:
            return
        if value not in emails:
            emails.add(value)

    # Step 1: Search first 10 rows for an email header
    email_column = None
    header_row = None

    #  both columns and rows in openpyxl use 1-based indexing
    for row_index,row in enumerate(worksheet.iter_rows(min_row=1, max_row=min(10, worksheet.max_row),values_only=True),1):
        for col_index,cell_value in enumerate(row,1):
            if isinstance(cell_value, str):
                if cell_value.strip().lower() in HEADER_NAMES:
                    email_column = col_index
                    header_row = row_index
                    break

        if email_column is not None and header_row is not None:
            break


    # Step 2: If header found, scan only that column
    if email_column is not None and header_row is not None:
        for value in worksheet.iter_rows(min_row=header_row+1,min_col=email_column,max_col=email_column,values_only=True):
            if value:
                add_email(value[0])

            if len(emails) >= MAX_EMAILS:
                break

        return {
            'emails':emails,
            'count': len(emails),
            'header_used': True,
        }

    # Step 3: Fallback - scan every cell
    for row in worksheet.iter_rows(values_only = True):
        for cell_value in row:
            add_email(cell_value)
            if len(emails) >= MAX_EMAILS:
                return {
                    'emails': emails,
                    'count': len(emails),
                    'header_used': False,
                }
    return {
        'emails': emails,
        'count': len(emails),   
        'header_used': False,
    }
                
def generate_numeric_otp(length=6):
    """Generates a secure, unpredictable numeric string"""
    digits = "0123456789"
    otp = "".join(secrets.choice(digits) for _ in range(length))
    return otp

def delete_root_org_otp_key(user_id:int,org_id:int):
    return f"otp:delete_root:{org_id}:{user_id}"