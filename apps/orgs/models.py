from django.db import models
from apps.users.models import User
# Sligify and unique slug names among siblings and max_depth, implement them in form clean()
# Make sure at the leaf there are only classes, no orgs
from django.utils.text import slugify
from treebeard.mp_tree import MP_Node

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

    # Links directly to one specific node in the tree
    org = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name="classes", 
        related_query_name="class"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['org', 'slug'], 
                name='unique_class_slug_per_org' # Create composite key, the two fields have to unique together
            )
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
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
    belongs_to = models.ForeignKey(
        Class, 
        on_delete=models.CASCADE, 
        related_name="memberships", 
        related_query_name="membership"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Prevents a user from joining the exact same class multiple times
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'belongs_to'], 
                name='unique_user_per_class'
            )
        ]

    def __str__(self):
        return f"{self.user.username} in {self.belongs_to.name}"
    
# While entering the name check if the name is valid or not, for slugs. All siblings should be unique

