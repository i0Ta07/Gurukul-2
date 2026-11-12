from django.db import models
from apps.orgs.models import Organization
from apps.users.models import User
from datetime import timedelta

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
    index = models.PositiveIntegerField()
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
