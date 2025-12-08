from django.urls import path
from . import api_views
urlpatterns = [
    path('exams/', api_views.ExamListAPI.as_view(), name='api_exam_list'),
    path('exams/<int:pk>/start/', api_views.start_exam, name='api_start_exam'),
    path('attempts/<int:attempt_id>/', api_views.attempt_detail, name='api_attempt_detail'),
    path('attempts/<int:attempt_id>/submit/', api_views.api_submit_attempt, name='api_submit_attempt'),
]
