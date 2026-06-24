from typing import Literal
from django.core.exceptions import ValidationError

from django.db import models
from apps.users.models import User
# Sligify and unique slug names among siblings and max_depth, implement them in form clean()
# Make sure at the leaf there are only classes, no orgs
from django.utils.text import slugify
from treebeard.mp_tree import MP_Node
import uuid
from config.settings import MAX_DEPTH

# ForeignKey field, child --> parent; Reverse(related_name), parent --> children
class Organization(MP_Node):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    # Used as related_name = user.created_orgs.all(); related_query_name = User.objects.filter(created_org__name = "SomeName")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_orgs', 
        related_query_name='created_org'
    )
    is_active = models.BooleanField(default=True)
    node_order_by = ['name']

    # If saved via standard ORM (not Treebeard's move/add methods), ensure slug exists
    # clean() is called by full_clean() -> when we submit using model forms. If using Admin panel, call it in save()
    def clean(self):
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)
        
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        # Treebeard allows you to visually indent strings for debugging!
        return f"{'--' * (self.depth - 1)} {self.name} (ID: {self.id})"

# Any node that inherits MP_Node will be a tree. Create using .add_root()
# harvard = Organization.add_root(name="Harvard University", slug="harvard", created_by=teacher)
# cse = harvard.add_child(name="Computer Science", slug="cse", created_by=teacher)


# Clean slug names with siblings in the form.
class Class(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(max_length=100)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_classes', 
        related_query_name='created_class'
    )
    is_active = models.BooleanField(default=True)
    code = models.UUIDField(unique=True,default=uuid.uuid4) # Callable, not the actual instance with (),if uuid4(), same uuid for every class

    # Links directly to one specific node in the tree
    org = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name="classes", 
        related_query_name="classroom"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['org', 'slug'], 
                name='unique_class_slug_per_org' # Create composite key, the two fields have to unique together
            )
        ]

# Classes cannot be creted at root_level since they need a org to connect to.
    def clean(self):
        super().clean()
        self.slug = self.slug or slugify(self.name)

        if self.org.get_children().exists():
            raise ValidationError('Classes cannot be created in the same folder in which orgs exist.')

        # If the class lies within the same org with the same slug name
        duplicate_classes = Class.objects.filter(org = self.org, slug = self.slug)
        if self.pk:
            duplicate_classes  = duplicate_classes.exclude(pk= self.pk)

        if duplicate_classes.exists():
            raise ValidationError({
                "name": f"A class named '{self.name}' already exists within {self.org.name}."
            })
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.org.name})"


class ClassMembership(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='memberships', 
        related_query_name='membership'
    )
    classroom = models.ForeignKey(
        Class, 
        on_delete=models.CASCADE, 
        related_name="memberships", 
        related_query_name="membership"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Prevents a user from joining the exact same class multiple times


    def __str__(self):
        return f"{self.user.username} in {self.classroom.name}"
    

def _validate_org_structure(ref_node: Organization, instance: Organization, position: Literal["sorted-child","sorted-sibling"] = "sorted-child"):
    """
    ref_node: when move ->  ref_node; when create: current_object
    instance: when move -> existing_node; when create: new_node
    position: when move -> position w.r.t. to ref_node; when create: child or sibling w.r.t. to current object

    """
    
    
    data = _get_parent(ref_node=ref_node,position=position)
    target_depth = data['target_depth']
    parent_node = data['parent_node']

    # --- RULE 1: Maximum Depth Limit (5) ---
    
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

    # --- RULE 2: Scoped Sibling Uniqueness & Classes at leaf nodes ---

    if parent_node:
        siblings = parent_node.get_children()
        if parent_node.classes.exists():
            raise ValidationError(f'Organization and classes cannot be in same folder.')
    else:
        siblings = Organization.get_root_nodes()

    # When moving, siblings also contains the current node, so exclude that.
    if instance.pk:
        siblings = siblings.exclude(pk=instance.pk)

    slug = instance.slug or slugify(instance.name)

    if siblings.filter(slug=slug).exists():
        raise ValidationError({
            "name": f"An organization with the name '{instance.name}' already exists at this exact level."
        })

# p1.add_sibling(pos = "sibling",p2)


def _get_parent(ref_node:Organization = None, position: Literal["sorted-child","sorted-sibling"] = "sorted-child") -> dict:
    """
    Move: ref_node = given in arg like node.move(ref_node= node1, pos="sorted-child")
    Create: ref_node = that invokes the method like node.add_sibling() 
    Gives the expected parent and target_depth, after successful create/move.
    """

    # Calculate what the depth and parent will be based on the ref_node and position
    if ref_node:
        if position == "sorted-child":
            target_depth = ref_node.depth + 1
            parent_node = ref_node
        else:
            target_depth = ref_node.depth
            parent_node = ref_node.get_parent()
    # No ref_node means it's being added as a root node
    else:
        target_depth = 1
        parent_node = None

    return {
        "target_depth":target_depth,
        "parent_node":parent_node
    }