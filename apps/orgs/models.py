from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from django.db import models
from apps.users.models import User
# Sligify and unique slug names among siblings and max_depth, implement them in form clean()
# Make sure at the leaf there are only classrooms, no orgs
from django.utils.text import slugify
from treebeard.mp_tree import MP_Node

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

    DEFAULT_TEMPLATES = {
        OrganizationType.COLLEGE: ("Departments", "Programs", "Year", "Semester", "Sections","Subjects"),
        OrganizationType.SCHOOL: ("Grades","Sections","Subjects"),
        OrganizationType.TUITION: ("Grades","Sessions","Batch","Subjects"), # morning session batch 1
        OrganizationType.COACHING: ("Courses","Sessions", "Batch", "Subjects",),
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

def is_admin(org:Organization,teacher:User)-> bool:
    """
    Given an org and teacher, it returns whether the teacher is an admin inside an org.
    """
    return org.memberships.filter(
        admin__isnull = False,
        teacher = teacher
    ).exists()

# We will create a orgmembership, for only root orgs. Only teacher can be a part of org. Students will only see classrooms
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
        return f"{self.teacher.get_full_name()} ({self.org.name})"
    
    def clean(self):
        super().clean()
        if not self.org.is_root():
            raise ValidationError('Org membership can only exist with root organization.')
        
        if self.teacher.user_type != User.UserType.TEACHER:
            raise ValidationError('Only teachers can be a part of the organization.')
        
        if self.teacher == self.org.config.owner:
            raise ValidationError('Owners cannot have memberships.')
        
        if self.created_by != self.org.config.owner and not is_admin(self.org,self.created_by):
            raise ValidationError('Only the owner and admins can add teachers.')
        
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "org"], name="unique_org_membership",
                violation_error_message = "Teacher is already a member of this organization.",
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
        return f" {self.membership.teacher.get_full_name()} ({self.membership.org.name})"
    
        
    def clean(self):
        super().clean()

        if not self.membership.org.is_root():
            raise ValidationError('Admins can only be created with root level orgs.')
        
        if self.created_by != self.membership.org.config.owner and not is_admin(org=self.membership.org,teacher=self.created_by):
            raise ValidationError("Only owners and admins can create admins.")
    
class OrgInvitation(models.Model):
    to_user =  models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_invitations",
        related_query_name="received_invitation"
    )
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
        related_query_name="sent_invitation"
    )
    org = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name="invitations", 
        related_query_name="invitation"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["to_user","org"], name="unique_invitation",
                violation_error_message = "You already sent an invitation to this user",
            )
        ]
    
    def clean(self):
        super().clean()
        if not self.org.is_root():
            raise ValidationError('You can only invite teachers to root organizations.')
        
        if self.org.memberships.filter(teacher=self.to_user).exists():
            raise ValidationError('User is already the part of this organization')
        
        if self.to_user == self.from_user:
            raise ValidationError("You cannot invite yourself.")
        
        if self.org.config.owner != self.from_user and not is_admin(org = self.org, teacher=self.from_user):
            raise ValidationError("You dont have permission to send invitations.")
        
    def __str__(self):
        return f"{self.to_user}({self.org})"