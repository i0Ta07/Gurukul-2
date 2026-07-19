from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from django.db import models
from apps.users.models import User
# Sligify and unique slug names among siblings and max_depth, implement them in form clean()
# Make sure at the leaf there are only classes, no orgs
from django.utils.text import slugify
from treebeard.mp_tree import MP_Node
from config.settings import MAX_DEPTH

## Upadate certain fields in django

# ForeignKey field, child --> parent; Reverse(related_name), parent --> children
class Organization(MP_Node):
    name = models.CharField(max_length=50,validators=[RegexValidator(r'^[A-Za-z0-9 ]+$','Only alphanumeric characters with spaces are allowed.',)])
    slug = models.SlugField(max_length=50)
    # Used as related_name = user.created_orgs.all(); related_query_name = User.objects.filter(created_org__name = "SomeName")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, # During deetecatch the PROTECT error
        related_name='created_orgs', 
        related_query_name='created_org'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    node_order_by = ['name']

    # If saved via standard ORM (not Treebeard's move/add methods), ensure slug exists
    # form.is_valid calls full_clean(), when submit using model/Admin forms. It ill not be called if you create objects using ORM manually
        
    # When changing the name,we have to change the slug too
    def save(self, *args ,**kwargs):
        self.slug = slugify(self.name)
        if (
            update_fields := kwargs.get("update_fields")
        ) is not None and "name" in update_fields:
            kwargs["update_fields"] = {"slug"}.union(update_fields)
        super().save(*args,**kwargs)

    def __str__(self):
        # Treebeard allows you to visually indent strings for debugging!
        return f"{'--' * (self.depth - 1)} {self.name} (ID: {self.id})"

# Any node that inherits MP_Node will be a tree. Create using .add_root()
# harvard = Organization.add_root(name="Harvard University", slug="harvard", created_by=teacher)
# cse = harvard.add_child(name="Computer Science", slug="cse", created_by=teacher)


# Ensure that the node is a root node.
class OrgConfig(models.Model):
    class OrganizationType(models.TextChoices):
        COLLEGE = "CL", _("College")
        SCHOOL = "SC", _("School")
        TUITION = "TN", _("Tuition")
        COACHING = "CG", _("Coaching")
        OTHER = "OT", _("Other")

    DEFAULT_TEMPLATES = {
        OrganizationType.COLLEGE: ("Departments", "Programs", "Year", "Semester", "Sections","Subjects"),
        OrganizationType.SCHOOL: ("Grades","Sections","Subjects"),
        OrganizationType.TUITION: ("Grades","Sessions","Batch","Subjects"), # morning session batch 1
        OrganizationType.COACHING: ("Courses","Sessions", "Batch", "Subjects",),
        OrganizationType.OTHER: (), # If other, user can create it's own. We give generic labels.
    }

    org = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="config",
        primary_key=True,
    )
    type = models.CharField(
        max_length=2,
        choices=OrganizationType,
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="owned_orgs",
        related_query_name="owned_org",
    )

    # bound to class rather than instace object, used to manage global attributes belonging strictly to the class namespace
    @classmethod
    def get_template(cls, organization_type):
        return cls.DEFAULT_TEMPLATES.get(organization_type, ())

    def template(self):
        return self.get_template(self.type)
    
    # def clean(self):
    #     super().clean()
    #     if self.org and not self.org.is_root():
    #         raise ValidationError('Configurations can only be created for root nodes.')
    
    def __str__(self):
        return f" {self.org.name} {self.owner} ({self.get_type_display()})"


# We will create a orgmembership, for only root orgs. Only teacher can be a part of org. Students will only see classes
# While accessing any org or it's child we will check if there is Orgmembership between the root and user if yes -> PERMITTED
# Also give option to create this using a .csv file. You have to manually add teachers to the organization.
class OrgMembership(models.Model):
    teacher = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='org_memberships', 
        related_query_name='org_membership'
    )
    org = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name="memberships", 
        related_query_name="membership"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        related_name='created_org_memberships', 
        related_query_name='created_org_membership'
    )

    def __str__(self):
        return f"{self.teacher.first_name} {self.teacher.last_name} ({self.org.name})"
    
    def clean(self):
        super().clean()
        if not self.org.is_root():
            raise ValidationError('Org membership can only exist with root organization.')
        
        if self.teacher.user_type != User.UserType.TEACHER:
            raise ValidationError('Only teachers can be a part of the organization.')
        
        if self.teacher == self.org.config.owner:
            raise ValidationError('Owners cannot have memberships.')
        
        if self.created_by != self.org.config.owner and not _is_admin(self.org,self.created_by):
            raise ValidationError('Only the owner and admins can add teachers.')
        
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "org"], name="unique_org_membership"
            )
        ]

class OrgAdmin(models.Model):
    """
    Can give admin status to an existing teacher.
    Teacher can create, update org and also add/remove members to an org.
    """

    # Each Orgmembership has exactly one to one relationship with OrgAdmin, no related query name or unique field checks.
    membership = models.OneToOneField(
        OrgMembership,
        on_delete=models.CASCADE,
        related_name="admin",
        primary_key=True,
    )

    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='created_admins', 
        related_query_name='created_admin'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f" {self.membership.teacher.first_name} {self.membership.teacher.last_name} ({self.membership.org.name})"
    
        
    def clean(self):
        super().clean()

        if not self.membership.org.is_root():
            raise ValidationError('Admins can only be created with root level orgs.')
        
        if self.created_by != self.membership.org.config.owner and not _is_admin(org=self.membership.org,teacher=self.created_by):
            raise ValidationError("Only owners and admins can create admins.")
    
def _is_admin(org:Organization,teacher:User)-> bool:
    """
    Given an org and teacher, it returns whether the teacher is an admin inside an org.
    """
    return org.memberships.filter(
        admin__isnull = False,
        teacher = teacher
    ).exists()

# in the root node we only have to validate the uniques sibling for else we have to additonally check if height < MAX_HEIGHT and classes exists
# also we are always adding child node, not sibling. When move we will move inside a org as a child not a sibling.
# node.move(ref_node= node1, pos="sorted-child")

def validate_root_org(instance:Organization):
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
        raise ValidationError(f'Organization and classes cannot be in same folder.')

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

    slug = instance.slug or slugify(instance.name)

    if siblings.filter(slug=slug).exists():
        raise ValidationError(f"The root name must be unique.")
