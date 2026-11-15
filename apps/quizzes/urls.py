from django.urls import path
from apps.quizzes.views import SearchQuizzesView

urlpatterns = [
    path('create/<int:org_id>',SearchQuizzesView.as_view(),name='search-quizzes'),

    ]