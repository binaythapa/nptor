# quiz/admin.py

import csv

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from accounts.models.client import Client

from .models import (
    Domain, Category, Difficulty, Question, Choice, QuestionFeedback,
    ExamTrack, Exam, TrackExam, Coupon, ExamCategoryAllocation, UserExam,
    UserAnswer, ExamUnlockLog, QuestionDiscussion, DiscussionVote,
    DiscussionReport, QuestionQualitySignal, PaymentRecord, StudyPlan,
    StudyPlanAnalyticsSnapshot, LeaderboardEntry,
)

# Load registrations for the scalable government-exam catalog.
from . import admin_government_catalog  # noqa: F401,E402

admin.site.register(Client)
admin.site.register(DiscussionVote)
admin.site.register(DiscussionReport)
admin.site.register(QuestionQualitySignal)

BULMA_WIDGET_OVERRIDES = {
    models.CharField: {"widget": forms.TextInput(attrs={"class": "input"})},