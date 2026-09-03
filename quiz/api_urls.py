from django.http import JsonResponse
from django.urls import path

from . import api_views
from quiz.services.access import can_access_exam
from quiz.models import Exam


def start_exam_authorized(request, pk):
    """Enforce exam access before delegating to the legacy API view."""
    exam = Exam.objects.filter(pk=pk, is_published=True).first()

    if exam is not None:
        allowed, reason = can_access_exam(request.user, exam)
        if not allowed:
            return JsonResponse(
                {"detail": reason},
                status=403,
            )

    return api_views.start_exam(request, pk)


urlpatterns = [
    path('exams/', api_views.ExamListAPI.as_view(), name='api_exam_list'),
    path('exams/<int:pk>/start/', start_exam_authorized, name='api_start_exam'),
    path('attempts/<int:attempt_id>/', api_views.attempt_detail, name='api_attempt_detail'),
    path('attempts/<int:attempt_id>/submit/', api_views.api_submit_attempt, name='api_submit_attempt'),
]
