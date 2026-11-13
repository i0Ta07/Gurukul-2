from django.db import models
from apps.classes.models import Classroom
from apps.orgs.models import Organization
from apps.users.models import User
from datetime import timedelta
import os,uuid
from django.utils.translation import gettext_lazy as _

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

class Attempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = 'P',_('In Progress')
        COMPLETED = 'C',_('Completed')
    student = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="attempts",
        related_query_name="attempt"
    )
    membership = models.ForeignKey(
        QuizClassMembership,
        on_delete=models.CASCADE,
        related_name="attempts",
        related_query_name="attempt"
    )
    sections_question_order = models.JSONField(default=list) # [{"section_id": 3, "question_ids": [12, 7, 9]}, {"section_id": 5, "question_ids": [4, 2]}]
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2,null=True,blank=True)
    total_marks = models.DecimalField(max_digits=6, decimal_places=2,blank=True,null=True)
    quiz_version = models.PositiveIntegerField()
    connects = models.PositiveIntegerField(default=0) # count number of connects, should not be >=3, user can 2 chances of reconnect.
    current_section_index = models.PositiveIntegerField(null=True,blank=True) # reject any answer whose question isn’t in the current section and in case of reconnect start from this section.
    status = models.CharField(
        choices=Status,
        default=Status.IN_PROGRESS,
        max_length=1
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['membership','student'],
                name='unique_attempt_per_membership'
            )
        ]
        indexes = [
            models.Index(fields=['membership', 'quiz_version'], name='membership_version_index'),
        ]

    def __str__(self):
        return f"{self.student_id}:{self.membership_id}"

class Answer(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
        related_query_name="answer"
    )
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name="answers",
        related_query_name="answer"
    )
    selected_options = models.JSONField(default=list)
    is_correct = models.BooleanField(blank=True,null=True)
    marks_awarded = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields= ['attempt','question'],
                name="unique_answer_per_question_per_attempt"
            )
        ]

    def __str__(self):
        return f"{self.attempt_id}:{self.question_id}"