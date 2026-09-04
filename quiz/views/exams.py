import math
import random
import logging

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode

from quiz.services.exam_question_allocator import allocate_questions_for_exam
from subscriptions.models import SubscriptionPlan, SubscriptionEntitlement
from subscriptions.services import SubscriptionService, AccessService
from organizations.models.access import ResourceAccess
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView
from courses.models import Course, Lesson
from courses.services.progress import get_next_lesson
from courses.services.quiz_completion import *
from quiz.forms import *
from quiz.models import Exam, ExamTrack, UserExam, UserAnswer, Question, QuestionFeedback, Coupon
from quiz.services.access import can_access_exam
from quiz.services.pricing import apply_coupon
from quiz.services.grading import grade_exam
from quiz.services.answer_persistence import autosave_answers
from quiz.utils import get_leaf_category_name
from core.utils.memory import get_memory_usage_mb

User = get_user_model()
logger = logging.getLogger("django")


def get_course_exam_redirect_url(context):
    """Return the course lesson URL stored in an exam context, if any."""
    if not context or not context.get("course_slug") or not context.get("lesson_id"):
        return None
    return reverse(
        "courses:course_learn_lesson",
        kwargs={
            "slug": context["course_slug"],
            "lesson_id": context["lesson_id"],
        },
    )

@login_required
def exam_start(request, exam_id):
    mem = get_memory_usage_mb()
    if mem is not None:
        logger.info(f"Exam Start page memory usage: {mem} MB")
    exam = get_object_or_404(Exam, pk=exam_id, is_published=True)
    course_slug = request.GET.get("course")
    lesson_id = request.GET.get("lesson")
    if course_slug and lesson_id:
        lesson = Lesson.objects.filter(id=lesson_id, lesson_type=Lesson.TYPE_QUIZ, exam=exam).first()
        if lesson:
            attempts = UserExam.objects.filter(user=request.user, exam=exam, submitted_at__isnull=False).count()
            if lesson.quiz_max_attempts and attempts >= lesson.quiz_max_attempts:
                messages.error(request, f"You have reached the maximum attempts ({lesson.quiz_max_attempts}) for this lesson.")
                return redirect("courses:course_learn_lesson", slug=course_slug, lesson_id=lesson.id)
            request.session["course_exam_context"] = {"course_slug": course_slug, "lesson_id": lesson.id}
    allowed, reason = can_access_exam(request.user, exam)
    if not allowed:
        messages.info(request, reason or "This exam is currently unavailable.")
        return redirect(f"{reverse('quiz:exam_locked', args=[exam.id])}?{urlencode({'reason': reason or ''})}")
    return redirect("quiz:student_dashboard")
