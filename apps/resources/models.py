from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid,os
from django.core.exceptions import ValidationError
from apps.resources.utils import clean_file_size
from config.validators import pdf_validator
from apps.classes.models import Classroom
from apps.orgs.models import Organization
from apps.users.models import User

class Resource(models.Model):
    class ResourceType(models.TextChoices):
        NOTES = 'NTS',_('Notes')
        PYQS = 'PYQ',_('Previous Year Questions')
        RESEARCH_PAPER = 'RSP',_('Research Papers')
        TEXTBOOK = 'TTB',_('Textbooks')
        ARTICLE = 'ATC',('Article')
        VIDEO = 'VDO',_('Video')
        SYLLABUS = 'SLB',_('Syllabus')
        QUESTION_BANK =  'QTB',_('Question Bank')
        CASE_STUDY = 'CSD',_('Case Study')
        CHEAT_SHEET = 'CTS',_('Cheat Sheet')
        ASSIGNMENT = 'ASM',_('Assignment')

    title = models.CharField(max_length=100)
    url = models.URLField(max_length=200, blank=True)
    type = models.CharField(
        max_length=3,
        choices = ResourceType,
    )

    def file_directory_path(instance, filename):
        _, extension = os.path.splitext(filename)
        return f"orgs/{instance.root_id}/resources/{uuid.uuid4()}{extension.lower()}"
    
    file  = models.FileField(upload_to=file_directory_path,blank=True,validators=[pdf_validator])
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="resources",
        related_query_name="resource"
    )
    root = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="resources",
        related_query_name="resource"
    )
    snapshots = models.JSONField(default=list,blank = True)

    def clean(self):
        super().clean()

        if bool(self.file) == bool(self.url):
            raise ValidationError("Provide either a URL or a file.")

        if self.file:
            clean_file_size(self.file,max_size=5)

    def __str__(self):
        return f"{self.title}:{self.root_id}"
        

class ResourceClassMembership(models.Model):
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="resource_memberships",
        related_query_name="resource_membership"
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name="memberships",
        related_query_name="membership"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_resource_memberships",
        related_query_name="created_resource_membership"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['classroom', 'resource'], 
                name='unique_classroom_resource_membership'
            )
        ]

    def __str__(self):
        return f"{self.classroom.name}: {self.resource.id}"


    def save(self, *args, **kwargs):
        if not self.pk:
            parent = self.classroom.parent
            ancestors = list(parent.get_ancestors())
            root = ancestors[0]

            hierarchy = ancestors[1:] + [parent] # remove root and add current parent
            template = root.config.template()

            snapshot = {
                key: node.name
                for key, node in zip(template, hierarchy)
            }
            snapshot["Subject"] = self.classroom.name

            snapshots = self.resource.snapshots
            snapshots.append(snapshot)

            if len(snapshots) > 5:
                del snapshots[:-5]

            self.resource.save(update_fields=["snapshots"])

        super().save(*args, **kwargs)