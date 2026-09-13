# quiz/views/admin_subscription_views.py
import logging
from datetime import timedelta
from decimal import Decimal

from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from organizations.models.access import ResourceAccess

from quiz.models import (
    Exam,
    ExamTrack,
    TrackExam,
    Coupon,
)

from subscriptions.models import (
    Subscription,
    SubscriptionEntitlement,
    SubscriptionPlan,
    Payment,
)

from subscriptions.services.plan_service import (
    get_plan_for_track,
    get_default_plan,
    get_plan_for_exam,
)

from subscriptions.services.subscription_service import (
    SubscriptionService,
)

from subscriptions.services.access_service import (
    AccessService,
)

User = get_user_model()
logger = logging.getLogger(__name__)

RESOURCE_EXAM = SubscriptionEntitlement.RESOURCE_EXAM
RESOURCE_TRACK = SubscriptionEntitlement.RESOURCE_TRACK


@staff_member_required
def subscription_admin_panel(request):
    now = timezone.now()
    users = User.objects.filter(is_active=True).order_by("username")
    tracks = ExamTrack.objects.prefetch_related("subscription_plans").filter(is_active=True).order_by("-created_at")
    exams = Exam.objects.prefetch_related("track_memberships__track").filter(is_published=True).order_by("-created_at")
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by("price", "name")

    entitlements = SubscriptionEntitlement.objects.select_related(
        "subscription", "subscription__user", "subscription__organization",
        "subscription__plan", "subscription__granted_by", "exam", "track",
    ).order_by("-created_at")

    exam_subs = []
    for entitlement in entitlements:
        if entitlement.resource_type != RESOURCE_EXAM or not entitlement.exam:
            continue
        subscription = entitlement.subscription
        is_active = (
            entitlement.is_active
            and subscription.status == Subscription.STATUS_ACTIVE
            and subscription.starts_at <= now
            and (subscription.expires_at is None or subscription.expires_at > now)
        )
        exam_subs.append({
            "id": entitlement.id,
            "user": subscription.user,
            "exam": entitlement.exam,
            "track": entitlement.exam.track_memberships.first().track if entitlement.exam.track_memberships.exists() else None,
            "subscription": subscription,
            "entitlement": entitlement,
            "is_active": is_active,
            "expires_at": subscription.expires_at,
            "subscribed_by_admin": subscription.subscribed_by_admin,
            "granted_by": subscription.granted_by,
            "amount": subscription.amount,
            "currency": subscription.currency,
        })

    track_subs = []
    for entitlement in entitlements:
        if entitlement.resource_type != RESOURCE_TRACK or not entitlement.track:
            continue
        subscription = entitlement.subscription
        is_active = (
            entitlement.is_active
            and subscription.status == Subscription.STATUS_ACTIVE
            and subscription.starts_at <= now
            and (subscription.expires_at is None or subscription.expires_at > now)
        )
        track_subs.append({
            "id": entitlement.id,
            "user": subscription.user,
            "track": entitlement.track,
            "subscription": subscription,
            "entitlement": entitlement,
            "is_active": is_active,
            "expires_at": subscription.expires_at,
            "subscribed_by_admin": subscription.subscribed_by_admin,
            "granted_by": subscription.granted_by,
            "amount": subscription.amount,
            "currency": subscription.currency,
        })

    return render(request, "quiz/student/subscription/dashboard.html", {
        "users": users,
        "tracks": tracks,
        "exams": exams,
        "plans": plans,
        "exam_subs": exam_subs,
        "track_subs": track_subs,
    })


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            "title",
            "question_count",
            "duration_seconds",
            "passing_score",
            "is_published",
            "max_mock_attempts",
        ]


class TrackForm(forms.ModelForm):
    exams = forms.ModelMultipleChoiceField(
        queryset=Exam.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10}),
        help_text="Select the reusable exams included in this Track. Exams are not sold separately.",
    )

    class Meta:
        model = ExamTrack
        fields = [
            "title", "slug", "description", "organization", "exams",
            "subscription_plans", "pricing_type", "monthly_price",
            "lifetime_price", "trial_days", "currency", "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "subscription_plans": forms.SelectMultiple(attrs={"size": 8}),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        exam_qs = Exam.objects.filter(is_published=True).order_by("title")
        if organization is not None:
            exam_qs = exam_qs.filter(organization=organization)
            self.fields["organization"].initial = organization
        self.fields["exams"].queryset = exam_qs
        self.fields["subscription_plans"].queryset = SubscriptionPlan.objects.filter(
            is_active=True,
            product_type=SubscriptionPlan.PRODUCT_TRACK,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
        ).order_by("price", "name")
        self.fields["subscription_plans"].help_text = (
            "Track product plans only. Buying a Track grants this Track and its included Exams."
        )
        if self.instance.pk:
            self.fields["exams"].initial = self.instance.track_exams.values_list("exam_id", flat=True)

    def clean(self):
        cleaned = super().clean()
        plans = cleaned.get("subscription_plans")
        pricing_type = cleaned.get("pricing_type")
        if plans and pricing_type != ExamTrack.PRICING_FREE:
            raise forms.ValidationError("Use Track Subscription Plans instead of legacy pricing.")
        return cleaned

    def save(self, commit=True):
        track = super().save(commit=commit)
        if commit:
            TrackExam.objects.filter(track=track).delete()
            for order, exam in enumerate(self.cleaned_data.get("exams") or [], start=1):
                TrackExam.objects.create(track=track, exam=exam, order=order)
        return track


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ["code", "percent_off", "flat_off", "track", "exam", "valid_from", "valid_to", "usage_limit", "extra_trial_days", "is_active"]
        widgets = {
            "valid_from": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "valid_to": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


@staff_member_required
def admin_exam_list(request):
    exams = Exam.objects.prefetch_related("track_memberships__track").order_by("-created_at")
    return render(request, "quiz/student/subscription/exam_list.html", {"exams": exams})


@staff_member_required
def admin_exam_create(request):
    form = ExamForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("quiz:admin_exam_list")
    return render(request, "quiz/student/subscription/exam_form.html", {"form": form, "mode": "create"})


@staff_member_required
def admin_exam_update(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    form = ExamForm(request.POST or None, instance=exam)
    if form.is_valid():
        form.save()
        return redirect("quiz:admin_exam_list")
    return render(request, "quiz/student/subscription/exam_form.html", {"form": form, "mode": "edit"})


@staff_member_required
def admin_exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    exam.delete()
    return redirect("quiz:admin_exam_list")


@staff_member_required
def admin_track_list(request):
    tracks = ExamTrack.objects.prefetch_related("subscription_plans", "track_exams__exam").order_by("-created_at")
    return render(request, "quiz/student/subscription/track_list.html", {"tracks": tracks})


@staff_member_required
def admin_track_create(request):
    form = TrackForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("quiz:admin_track_list")
    return render(request, "quiz/student/subscription/track_form.html", {"form": form, "mode": "create"})


@staff_member_required
def admin_track_update(request, pk):
    track = get_object_or_404(ExamTrack, pk=pk)
    form = TrackForm(request.POST or None, instance=track)
    if form.is_valid():
        form.save()
        return redirect("quiz:admin_track_list")
    return render(request, "quiz/student/subscription/track_form.html", {"form": form, "mode": "edit"})


@staff_member_required
def admin_track_delete(request, pk):
    track = get_object_or_404(ExamTrack, pk=pk)
    track.delete()
    return redirect("quiz:admin_track_list")


@staff_member_required
def admin_coupon_list(request):
    coupons = Coupon.objects.order_by("-created_at")
    return render(request, "quiz/student/subscription/coupon_list.html", {"coupons": coupons})


@staff_member_required
def admin_coupon_create(request):
    form = CouponForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("quiz:admin_coupon_list")
    return render(request, "quiz/student/subscription/coupon_form.html", {"form": form})


@staff_member_required
def admin_payment_list(request):
    payments = Payment.objects.select_related("user", "organization", "subscription", "subscription__plan").order_by("-created_at")
    context = {
        "payments": payments,
        "users": User.objects.filter(is_active=True).order_by("username"),
        "exams": Exam.objects.all(),
        "tracks": ExamTrack.objects.all(),
        "plans": SubscriptionPlan.objects.filter(is_active=True).order_by("price", "name"),
        "coupons": Coupon.objects.filter(is_active=True),
    }
    return render(request, "quiz/student/subscription/payment_list.html", context)
