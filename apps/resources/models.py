from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.classes.models import Classroom
from apps.classes.utils import generate_classroom_hierarchy
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
    url = models.URLField(max_length=200)
    type = models.CharField(
        max_length=3,
        choices = ResourceType,
    )
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

    def __str__(self):
        return f"{self.title}:{self.root_id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['url', 'root'], 
                name='unique_resource_inside_org'
            )
        ]
        

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
            hierarchies = generate_classroom_hierarchy(classrooms=[self.classroom])
            hierarchy = hierarchies[self.classroom_id]
            root = hierarchy.pop(0) # consume root
            template = root.config.template()

            snapshot = {
                key: node.name
                for key, node in zip(template, hierarchy)
            }
            snapshots = self.resource.snapshots
            if snapshot not in snapshots:
                snapshots.append(snapshot)

                if len(snapshots) > 5:
                    del snapshots[:-5]

                self.resource.save(update_fields=["snapshots"])

        super().save(*args, **kwargs)