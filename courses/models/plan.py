from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from ckeditor.fields import RichTextField

from quiz.models import *




from django.db import models


class SubscriptionPlan(models.Model):
    PLAN_TYPE_CHOICES = (
        ("course", "Course"),
        ("exam", "Exam"),
        ("track", "Track"),
    )

    name = models.CharField(max_length=100)
    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPE_CHOICES
    )

    duration_days = models.PositiveIntegerField(
        help_text="Access duration in days"
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=10,
        default="INR"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.duration_days} days)"