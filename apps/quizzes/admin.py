from django.contrib import admin
from apps.quizzes.models import Quiz,Section,Question,QuizClassMembership,Attempt,Answer

# Register your models here.
admin.site.register(Quiz)
admin.site.register(Section)
admin.site.register(Question)
admin.site.register(QuizClassMembership)
admin.site.register(Attempt)
admin.site.register(Answer)