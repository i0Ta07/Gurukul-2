from django.db import models
import uuid
from django.core.exceptions import ValidationError
from apps.users.models import User
from apps.orgs.models import Organization
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Class(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    code = models.UUIDField(unique=True,default=uuid.uuid4) # Callable, not the actual instance with (),if uuid4(), same uuid for every class
    members = models.ManyToManyField(
        User,
        through="ClassMembership",
        related_name="classrooms",
        related_query_name="classroom",
    )
    # Links directly to one specific node in the tree
    org = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name="classrooms", 
        related_query_name="classroom"
    )    
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='owned_classrooms', 
        related_query_name='owned_classroom'
    )

    # Classes cannot be created at root_level since they need a org to connect to.
    def clean(self):
        super().clean()

        if self.org.get_children().exists():
            raise ValidationError('Classes cannot be created in the same folder in which orgs exist.')

        self.slug = slugify(self.name)

        # If the class lies within the same org with the same slug name
        duplicate_classes = Class.objects.filter(org = self.org, slug = self.slug)
        if self.pk:
            duplicate_classes  = duplicate_classes.exclude(pk= self.pk)

        if duplicate_classes.exists():
            raise ValidationError(f"A class named '{self.name}' already exists within {self.org.name}.")

        # When changing the name,we have to change the slug too
    def save(self, **kwargs):
        # Not calling self.full_clean(), since we will create using forms, 
        # if mentioned it will be called twice once in form.is_valid() and one in save.
        
        self.slug = slugify(self.name)
        if (
            update_fields := kwargs.get("update_fields")
        ) is not None and "name" in update_fields:
            kwargs["update_fields"] = {"slug"}.union(update_fields)
        super().save(**kwargs)

    def __str__(self):
        return f"{self.name} ({self.org.name})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['org', 'slug'], 
                name='unique_class_name_inside_org' # Create composite key, the two fields have to unique together
            )
        ]

# Teachers and students both can be a part of a class. Students can join the class using the uuid link but teachers 
# will be automatically joined during creation. Teachers can add other teachers to the class, but there has to be 
# atleast one teacher in the class at all times. To make sure teachers cannot join the classrooms using the link, 
# we have to validate it inside the join view.
class ClassMembership(models.Model):
    class Status(models.TextChoices):
        ACCEPTED = 'A',_('Accepted')
        REVOKED = 'R',_('Revoked')
        
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='classroom_memberships', 
        related_query_name='classroom_membership'
    )
    classroom = models.ForeignKey(
        Class, 
        on_delete=models.CASCADE, 
        related_name="memberships", 
        related_query_name="membership"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        choices=Status,
        default=Status.ACCEPTED,
        max_length=1
    )

    def __str__(self):
        return f"{self.user.username} in {self.classroom.name}"
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "classroom"], name="unique_class_membership"
            )
        ]