from django.db import models
from apps.classes.models import Classroom
from apps.orgs.models import Organization
from apps.users.models import User
from datetime import timedelta
import os,uuid

class Quiz(models.Model):
    root = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="quizzes",
        related_query_name="quiz"
    )
    title = models.CharField(max_length=200)
    time_limit = models.DurationField(default=timedelta(hours=1))
    switch_sections = models.BooleanField(default=True)
    marks_per_question = models.DecimalField(max_digits=4,decimal_places=2,default=1)
    negative_marks_per_question = models.DecimalField(max_digits=4,decimal_places=2,default=0)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="quizzes",
        related_query_name="quiz"
    )
    version = models.PositiveIntegerField(default=1) # lock this on ongoing attempt
    total_marks = models.DecimalField(max_digits=6, decimal_places=2,blank=True,null=True) # change everytime you delete or add a question
    snapshots = models.JSONField(default=list,blank = True)

    def __str__(self):
        return f"{self.title}:{self.root_id}"

class Section(models.Model):
    title = models.CharField(max_length=200)
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="sections",
        related_query_name="section"
    )
    index = models.PositiveIntegerField() # order of the section
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="sections",
        related_query_name="section"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['quiz', 'index'], 
                name='unique_index_per_quiz'
            )
        ]

    def __str__(self):
        return f"{self.title}:{self.quiz_id}:{self.index}"

class Question(models.Model):
    text = models.CharField(max_length=800)
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="questions",
        related_query_name="question"
    )
    
    def question_images_directory_path(instance, filename):
        _, extension = os.path.splitext(filename)
        return f"questions/images/{instance.section_id}/{uuid.uuid4()}{extension.lower()}"
    
    image = models.ImageField(blank = True,upload_to=question_images_directory_path,)
    options = models.JSONField(default=list) # [{'id':.. , 'text': .. , 'is_correct': .. },...]
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="questions",
        related_query_name="question"
    )
    updated_at = models.DateTimeField(auto_now=True)
    accuracy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.section_id}: {self.id}"

class QuizClassMembership(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="memberships",
        related_query_name="membership"
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="quiz_memberships",
        related_query_name="quiz_membership"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="quiz_memberships",
        related_query_name="quiz_membership"
    )
    published = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['quiz','classroom'],
                name='unique_classroom_quiz_membership'
            )
        ]

    def __str__(self):
        return f"{self.quiz_id}:{self.classroom_id}"
