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


# ============================================================
# USER MODEL
# ============================================================

User = get_user_model()

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS
# ============================================================

RESOURCE_EXAM = SubscriptionEntitlement.RESOURCE_EXAM
RESOURCE_TRACK = SubscriptionEntitlement.RESOURCE_TRACK


# ============================================================
# HELPERS
# ============================================================

# ============================================================
# ADMIN SUBSCRIPTION PANEL
# ============================================================
@staff_member_required
def subscription_admin_panel(request):
    now = timezone.now()

    # ============================================================
    # USERS
    # ============================================================

    users = (
        User.objects
        .filter(is_active=True)
        .order_by("username")
    )

    # ============================================================
    # TRACKS
    # ============================================================

    tracks = (
        ExamTrack.objects
        .prefetch_related("subscription_plans")
        .filter(is_active=True)
        .order_by("-created_at")
    )

    # ============================================================
    # EXAMS
    # ============================================================

    exams = (
        Exam.objects
        .select_related("track")
        .filter(is_published=True)
        .order_by("-created_at")
    )

    # ============================================================
    # PLANS
    # ============================================================

    plans = (
        SubscriptionPlan.objects
        .filter(is_active=True)
        .order_by("price", "name")
    )

    # ============================================================
    # SUBSCRIPTION ENTITLEMENTS
    #
    # New architecture:
    #
    # User
    #   ↓
    # Subscription
    #   ↓
    # SubscriptionEntitlement
    #   ↓
    # Exam / Track
    #
    # ============================================================

    entitlements = (
        SubscriptionEntitlement.objects
        .select_related(
            "subscription",
            "subscription__user",
            "subscription__organization",
            "subscription__plan",
            "subscription__granted_by",
            "exam",
            "track",
        )
        .order_by("-created_at")
    )

    # ============================================================
    # BUILD EXAM SUBSCRIPTIONS FOR TEMPLATE
    # ============================================================

    exam_subs = []

    for entitlement in entitlements:

        if entitlement.resource_type != (
            SubscriptionEntitlement.RESOURCE_EXAM
        ):
            continue

        if not entitlement.exam:
            continue

        subscription = entitlement.subscription

        # Effective active status
        is_active = (
            entitlement.is_active
            and subscription.status == Subscription.STATUS_ACTIVE
            and subscription.starts_at <= now
            and (
                subscription.expires_at is None
                or subscription.expires_at > now
            )
        )

        exam_subs.append({
            "id": entitlement.id,
            "user": subscription.user,
            "exam": entitlement.exam,
            "track": entitlement.exam.track,
            "subscription": subscription,
            "entitlement": entitlement,

            "is_active": is_active,

            "expires_at": subscription.expires_at,

            "subscribed_by_admin": (
                subscription.subscribed_by_admin
            ),

            "granted_by": subscription.granted_by,

            "amount": subscription.amount,
            "currency": subscription.currency,
        })

    # ============================================================
    # BUILD TRACK SUBSCRIPTIONS FOR TEMPLATE
    # ============================================================

    track_subs = []

    for entitlement in entitlements:

        if entitlement.resource_type != (
            SubscriptionEntitlement.RESOURCE_TRACK
        ):
            continue

        if not entitlement.track:
            continue

        subscription = entitlement.subscription

        # Effective active status
        is_active = (
            entitlement.is_active
            and subscription.status == Subscription.STATUS_ACTIVE
            and subscription.starts_at <= now
            and (
                subscription.expires_at is None
                or subscription.expires_at > now
            )
        )

        track_subs.append({
            "id": entitlement.id,
            "user": subscription.user,
            "track": entitlement.track,
            "subscription": subscription,
            "entitlement": entitlement,

            "is_active": is_active,

            "expires_at": subscription.expires_at,

            "subscribed_by_admin": (
                subscription.subscribed_by_admin
            ),

            "granted_by": subscription.granted_by,

            "amount": subscription.amount,
            "currency": subscription.currency,
        })

    # ============================================================
    # ALL SUBSCRIPTIONS
    # ============================================================

    subscriptions = (
        Subscription.objects
        .select_related(
            "user",
            "organization",
            "plan",
            "granted_by",
        )
        .prefetch_related(
            "entitlements",
            "entitlements__exam",
            "entitlements__track",
        )
        .order_by("-created_at")
    )

    # ============================================================
    # COUPONS
    # ============================================================

    coupons = (
        Coupon.objects
        .all()
        .order_by("-valid_to")
    )

    # ============================================================
    # CONTEXT
    # ============================================================

    context = {
        "users": users,
        "tracks": tracks,
        "exams": exams,
        "plans": plans,

        # IMPORTANT:
        # These are what the current HTML expects.
        "exam_subs": exam_subs,
        "track_subs": track_subs,

        # Keep this available if other dashboard sections use it.
        "subscriptions": subscriptions,

        "coupons": coupons,
        "now": now,
    }

    return render(
        request,
        "quiz/student/subscription/dashboard.html",
        context,
    )





















# ============================================================
# ADMIN: SUBSCRIBE TO TRACK
# ============================================================

@staff_member_required
@require_POST
def admin_subscribe_track(request):

    user = get_object_or_404(
        User,
        id=request.POST.get("user_id"),
    )

    track = get_object_or_404(
        ExamTrack,
        id=request.POST.get("track_id"),
    )

    plan = get_plan_for_track(
        track,
        request.POST.get("plan_id"),
    )

    if not plan:
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "No active subscription plan "
                    "is attached to this track."
                ),
            },
            status=400,
        )

    try:

        subscription, entitlement = (
            SubscriptionService.create_or_reactivate_subscription(
                user=user,
                resource_type=RESOURCE_TRACK,
                resource=track,
                plan=plan,
                granted_by=request.user,
                notes="Admin manual track subscription",
            )
        )

        AccessService.grant_access(
            user=user,
            resource_type=RESOURCE_TRACK,
            resource=track,
            source=ResourceAccess.SOURCE_ADMIN,
            subscription=subscription,
            expires_at=subscription.expires_at,
        )

        return JsonResponse(
            {
                "success": True,
                "subscription_id": subscription.id,
                "entitlement_id": entitlement.id,
            }
        )

    except Exception as exc:

        logger.exception(
            "Failed to subscribe user to track"
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================
# ADMIN: REVOKE TRACK
# ============================================================
@staff_member_required
@require_POST
@transaction.atomic
def admin_revoke_track(request):

    user = get_object_or_404(
        User,
        id=request.POST.get("user_id"),
    )

    track = get_object_or_404(
        ExamTrack,
        id=request.POST.get("track_id"),
    )

    try:
        # =====================================================
        # 1. Find current entitlement
        # =====================================================

        entitlement = SubscriptionService.get_user_resource_subscription(
            user=user,
            resource_type=RESOURCE_TRACK,
            resource=track,
        )

        if not entitlement:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Track entitlement not found.",
                },
                status=404,
            )

        subscription = entitlement.subscription

        # =====================================================
        # 2. Disable entitlement
        # =====================================================

        entitlement.is_active = False

        entitlement.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        # =====================================================
        # 3. Revoke ResourceAccess
        # =====================================================

        access_result = AccessService.revoke_access(
            user=user,
            resource_type=RESOURCE_TRACK,
            resource=track,
            source=ResourceAccess.SOURCE_ADMIN,
            subscription=subscription,
        )

        # =====================================================
        # 4. Cancel subscription if nothing remains
        # =====================================================

        has_other_active_entitlements = (
            SubscriptionEntitlement.objects
            .filter(
                subscription=subscription,
                is_active=True,
            )
            .exists()
        )

        if not has_other_active_entitlements:
            subscription.status = Subscription.STATUS_CANCELLED
            subscription.cancelled_at = timezone.now()

            subscription.save(
                update_fields=[
                    "status",
                    "cancelled_at",
                    "updated_at",
                ]
            )

        return JsonResponse(
            {
                "success": True,
                "access_revoked": access_result["access_revoked"],
                "access_count": access_result["access_count"],
            }
        )

    except Exception as exc:

        logger.exception(
            "Failed to revoke track subscription"
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )

# ============================================================
# ADMIN: SUBSCRIBE TO EXAM
# ============================================================

@staff_member_required
@require_POST
def admin_subscribe_exam(request):

    user = get_object_or_404(
        User,
        id=request.POST.get("user_id"),
    )

    exam = get_object_or_404(
        Exam,
        id=request.POST.get("exam_id"),
    )

    plan = get_plan_for_exam(
        exam,
        request.POST.get("plan_id"),
    )

    if not plan:

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "No active subscription plan "
                    "is available."
                ),
            },
            status=400,
        )

    try:

        subscription, entitlement = (
            SubscriptionService.create_or_reactivate_subscription(
                user=user,
                resource_type=RESOURCE_EXAM,
                resource=exam,
                plan=plan,
                granted_by=request.user,
                notes="Admin manual exam subscription",
            )
        )

        AccessService.grant_access(
            user=user,
            resource_type=RESOURCE_EXAM,
            resource=exam,
            source=ResourceAccess.SOURCE_ADMIN,
            subscription=subscription,
            expires_at=subscription.expires_at,
        )

        return JsonResponse(
            {
                "success": True,
                "subscription_id": subscription.id,
                "entitlement_id": entitlement.id,
            }
        )

    except Exception as exc:

        logger.exception(
            "Failed to subscribe user to exam"
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================
# ADMIN: REVOKE EXAM
# ============================================================
@staff_member_required
@require_POST
@transaction.atomic
def admin_revoke_exam(request):

    user = get_object_or_404(
        User,
        id=request.POST.get("user_id"),
    )

    exam = get_object_or_404(
        Exam,
        id=request.POST.get("exam_id"),
    )

    try:
        # =====================================================
        # 1. Find current entitlement
        # =====================================================

        entitlement = SubscriptionService.get_user_resource_subscription(
            user=user,
            resource_type=RESOURCE_EXAM,
            resource=exam,
        )

        if not entitlement:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Exam entitlement not found.",
                },
                status=404,
            )

        subscription = entitlement.subscription

        # =====================================================
        # 2. Disable entitlement
        # =====================================================

        entitlement.is_active = False

        entitlement.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        # =====================================================
        # 3. Revoke ResourceAccess
        # =====================================================

        access_result = AccessService.revoke_access(
            user=user,
            resource_type=RESOURCE_EXAM,
            resource=exam,
            source=ResourceAccess.SOURCE_ADMIN,
            subscription=subscription,
        )

        # =====================================================
        # 4. Cancel subscription if no active entitlements remain
        # =====================================================

        has_other_active_entitlements = (
            SubscriptionEntitlement.objects
            .filter(
                subscription=subscription,
                is_active=True,
            )
            .exists()
        )

        if not has_other_active_entitlements:
            subscription.status = Subscription.STATUS_CANCELLED
            subscription.cancelled_at = timezone.now()

            subscription.save(
                update_fields=[
                    "status",
                    "cancelled_at",
                    "updated_at",
                ]
            )

        return JsonResponse(
            {
                "success": True,
                "access_revoked": access_result["access_revoked"],
                "access_count": access_result["access_count"],
            }
        )

    except Exception as exc:

        logger.exception(
            "Failed to revoke exam subscription"
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )
# ============================================================
# TOGGLE TRACK ACTIVE STATUS
# ============================================================

@staff_member_required
@require_POST
def toggle_track_status(request):

    track_id = request.POST.get(
        "track_id"
    )

    try:

        track = ExamTrack.objects.get(
            id=track_id
        )

        track.is_active = not track.is_active

        track.save(
            update_fields=[
                "is_active",
            ]
        )

        return JsonResponse(
            {
                "success": True,
                "new_status": track.is_active,
            }
        )

    except ExamTrack.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Track not found",
            },
            status=404,
        )


# ============================================================
# TOGGLE COUPON ACTIVE STATUS
# ============================================================

@staff_member_required
@require_POST
def toggle_coupon_status(request):

    coupon_id = request.POST.get(
        "coupon_id"
    )

    try:

        coupon = Coupon.objects.get(
            id=coupon_id
        )

        coupon.is_active = not coupon.is_active

        coupon.save(
            update_fields=[
                "is_active",
            ]
        )

        return JsonResponse(
            {
                "success": True,
                "new_status": coupon.is_active,
            }
        )

    except Coupon.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Coupon not found",
            },
            status=404,
        )


# ============================================================
# CREATE COUPON
# ============================================================

@staff_member_required
@require_POST
def create_coupon_ajax(request):

    code = (
        request.POST.get("code") or ""
    ).strip().upper()

    percent_off = (
        request.POST.get("percent_off")
        or None
    )

    flat_off = (
        request.POST.get("flat_off")
        or None
    )

    try:

        valid_days = int(
            request.POST.get(
                "valid_days",
                7,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        valid_days = 7

    if not code:

        return JsonResponse(
            {
                "success": False,
                "error": "Coupon code is required",
            },
            status=400,
        )

    if Coupon.objects.filter(
        code=code
    ).exists():

        return JsonResponse(
            {
                "success": False,
                "error": "Coupon already exists",
            },
            status=400,
        )

    try:

        Coupon.objects.create(
            code=code,
            percent_off=(
                int(percent_off)
                if percent_off
                else None
            ),
            flat_off=(
                Decimal(flat_off)
                if flat_off
                else None
            ),
            valid_from=timezone.now(),
            valid_to=(
                timezone.now()
                + timedelta(
                    days=valid_days
                )
            ),
            is_active=True,
        )

    except Exception as exc:

        logger.exception(
            "Failed to create coupon"
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )

    return JsonResponse(
        {
            "success": True,
        }
    )


# ============================================================
# UPDATE TRACK PRICING TYPE
# ============================================================

@staff_member_required
@require_POST
def update_track_pricing_type(request):

    track_id = request.POST.get(
        "track_id"
    )

    pricing_type = request.POST.get(
        "pricing_type"
    )

    monthly_price = (
        request.POST.get(
            "monthly_price"
        )
        or None
    )

    lifetime_price = (
        request.POST.get(
            "lifetime_price"
        )
        or None
    )

    try:

        track = ExamTrack.objects.get(
            id=track_id
        )

        track.pricing_type = pricing_type

        if pricing_type == "free":

            track.monthly_price = None
            track.lifetime_price = None

        elif pricing_type == "monthly":

            if not monthly_price:

                return JsonResponse(
                    {
                        "success": False,
                        "error": (
                            "Monthly price required"
                        ),
                    },
                    status=400,
                )

            track.monthly_price = monthly_price
            track.lifetime_price = None

        elif pricing_type == "lifetime":

            if not lifetime_price:

                return JsonResponse(
                    {
                        "success": False,
                        "error": (
                            "Lifetime price required"
                        ),
                    },
                    status=400,
                )

            track.lifetime_price = lifetime_price
            track.monthly_price = None

        else:

            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid pricing type",
                },
                status=400,
            )

        track.save()

        return JsonResponse(
            {
                "success": True,
            }
        )

    except ExamTrack.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Track not found",
            },
            status=404,
        )


# ============================================================
# UPDATE EXAM SUBSCRIPTION EXPIRY
# ============================================================

@staff_member_required
@require_POST
def admin_update_exam_expiry(request):

    user_id = request.POST.get(
        "user_id"
    )

    exam_id = request.POST.get(
        "exam_id"
    )

    expires_at = request.POST.get(
        "expires_at"
    )

    user = get_object_or_404(
        User,
        id=user_id,
    )

    exam = get_object_or_404(
        Exam,
        id=exam_id,
    )

    entitlement = SubscriptionService.get_user_resource_subscription(
        user=user,
        resource_type=RESOURCE_EXAM,
        resource=exam,
    )

    if not entitlement:

        return JsonResponse(
            {
                "success": False,
                "error": "Subscription not found",
            },
            status=404,
        )

    subscription = entitlement.subscription

    if expires_at:

        from django.utils.dateparse import parse_datetime

        parsed = parse_datetime(
            expires_at
        )

        if parsed is None:

            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid expiry date",
                },
                status=400,
            )

        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(
                parsed
            )

        subscription.expires_at = parsed

    else:

        subscription.expires_at = None

    subscription.status = (
        Subscription.STATUS_ACTIVE
    )

    subscription.cancelled_at = None

    subscription.save(
        update_fields=[
            "expires_at",
            "status",
            "cancelled_at",
            "updated_at",
        ]
    )

    return JsonResponse(
        {
            "success": True,
        }
    )


# ============================================================
# UPDATE TRACK SUBSCRIPTION EXPIRY
# ============================================================

@staff_member_required
@require_POST
def admin_update_track_expiry(request):

    user_id = request.POST.get(
        "user_id"
    )

    track_id = request.POST.get(
        "track_id"
    )

    expires_at = request.POST.get(
        "expires_at"
    )

    user = get_object_or_404(
        User,
        id=user_id,
    )

    track = get_object_or_404(
        ExamTrack,
        id=track_id,
    )

    entitlement = SubscriptionService.get_user_resource_subscription(
        user=user,
        resource_type=RESOURCE_TRACK,
        resource=track,
    )

    if not entitlement:

        return JsonResponse(
            {
                "success": False,
                "error": "Subscription not found",
            },
            status=404,
        )

    subscription = entitlement.subscription

    if expires_at:

        from django.utils.dateparse import parse_datetime

        parsed = parse_datetime(
            expires_at
        )

        if parsed is None:

            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid expiry date",
                },
                status=400,
            )

        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(
                parsed
            )

        subscription.expires_at = parsed

    else:

        subscription.expires_at = None

    subscription.status = (
        Subscription.STATUS_ACTIVE
    )

    subscription.cancelled_at = None

    subscription.save(
        update_fields=[
            "expires_at",
            "status",
            "cancelled_at",
            "updated_at",
        ]
    )

    return JsonResponse(
        {
            "success": True,
        }
    )


# ============================================================
# ADD EXAM SUBSCRIPTION DAYS
# ============================================================

@staff_member_required
@require_POST
def admin_add_exam_days(request):

    try:

        user = get_object_or_404(
            User,
            id=request.POST["user_id"],
        )

        exam = get_object_or_404(
            Exam,
            id=request.POST["item_id"],
        )

        days = int(
            request.POST["days"]
        )

        if days <= 0:
            raise ValueError

        entitlement = SubscriptionService.get_user_resource_subscription(
            user=user,
            resource_type=RESOURCE_EXAM,
            resource=exam,
        )

        if not entitlement:

            return JsonResponse(
                {
                    "success": False,
                    "error": "Subscription not found",
                },
                status=404,
            )

        subscription = entitlement.subscription

        base_date = (
            subscription.expires_at
            or timezone.now()
        )

        subscription.expires_at = (
            base_date
            + timedelta(days=days)
        )

        subscription.status = (
            Subscription.STATUS_ACTIVE
        )

        subscription.cancelled_at = None

        subscription.save(
            update_fields=[
                "expires_at",
                "status",
                "cancelled_at",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "success": True,
                "expires_at": (
                    subscription.expires_at.isoformat()
                    if subscription.expires_at
                    else None
                ),
            }
        )

    except (
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid number of days",
            },
            status=400,
        )


# ============================================================
# ADD TRACK SUBSCRIPTION DAYS
# ============================================================

@staff_member_required
@require_POST
def admin_add_track_days(request):

    try:

        user = get_object_or_404(
            User,
            id=request.POST["user_id"],
        )

        track = get_object_or_404(
            ExamTrack,
            id=request.POST["item_id"],
        )

        days = int(
            request.POST["days"]
        )

        if days <= 0:
            raise ValueError

        entitlement = SubscriptionService.get_user_resource_subscription(
            user=user,
            resource_type=RESOURCE_TRACK,
            resource=track,
        )

        if not entitlement:

            return JsonResponse(
                {
                    "success": False,
                    "error": "Subscription not found",
                },
                status=404,
            )

        subscription = entitlement.subscription

        base_date = (
            subscription.expires_at
            or timezone.now()
        )

        subscription.expires_at = (
            base_date
            + timedelta(days=days)
        )

        subscription.status = (
            Subscription.STATUS_ACTIVE
        )

        subscription.cancelled_at = None

        subscription.save(
            update_fields=[
                "expires_at",
                "status",
                "cancelled_at",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "success": True,
                "expires_at": (
                    subscription.expires_at.isoformat()
                    if subscription.expires_at
                    else None
                ),
            }
        )

    except (
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid number of days",
            },
            status=400,
        )


# ============================================================
# FORMS
# ============================================================

class ExamForm(forms.ModelForm):

    class Meta:

        model = Exam

        fields = [
            "title",
            "track",
            "question_count",
            "duration_seconds",
            "passing_score",
            "is_free",
            "price",
            "currency",
            "is_published",
            "max_mock_attempts",
        ]


class TrackForm(forms.ModelForm):

    class Meta:

        model = ExamTrack

        fields = "__all__"

    def clean(self):

        cleaned = super().clean()

        plans = cleaned.get(
            "subscription_plans"
        )

        pricing_type = cleaned.get(
            "pricing_type"
        )

        if (
            plans
            and pricing_type
            != ExamTrack.PRICING_FREE
        ):

            raise forms.ValidationError(
                "Do not use legacy pricing when "
                "subscription plans are selected."
            )

        return cleaned


class CouponForm(forms.ModelForm):

    class Meta:

        model = Coupon

        fields = [
            "code",
            "percent_off",
            "flat_off",
            "track",
            "exam",
            "valid_from",
            "valid_to",
            "usage_limit",
            "extra_trial_days",
            "is_active",
        ]

        widgets = {

            "valid_from": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local"
                }
            ),

            "valid_to": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local"
                }
            ),

        }


# ============================================================
# EXAMS
# ============================================================

@staff_member_required
def admin_exam_list(request):

    exams = (
        Exam.objects
        .select_related("track")
        .order_by("-created_at")
    )

    return render(
        request,
        "quiz/student/subscription/exam_list.html",
        {
            "exams": exams,
        },
    )


@staff_member_required
def admin_exam_create(request):

    form = ExamForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            "quiz:admin_exam_list"
        )

    return render(
        request,
        "quiz/student/subscription/exam_form.html",
        {
            "form": form,
            "mode": "create",
        },
    )


@staff_member_required
def admin_exam_update(
    request,
    pk,
):

    exam = get_object_or_404(
        Exam,
        pk=pk,
    )

    form = ExamForm(
        request.POST or None,
        instance=exam,
    )

    if form.is_valid():

        form.save()

        return redirect(
            "quiz:admin_exam_list"
        )

    return render(
        request,
        "quiz/student/subscription/exam_form.html",
        {
            "form": form,
            "mode": "edit",
        },
    )


@staff_member_required
def admin_exam_delete(
    request,
    pk,
):

    exam = get_object_or_404(
        Exam,
        pk=pk,
    )

    exam.delete()

    return redirect(
        "quiz:admin_exam_list"
    )


# ============================================================
# TRACKS
# ============================================================

@staff_member_required
def admin_track_list(request):

    tracks = (
        ExamTrack.objects
        .prefetch_related(
            "subscription_plans"
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "quiz/student/subscription/track_list.html",
        {
            "tracks": tracks,
        },
    )


@staff_member_required
def admin_track_create(request):

    form = TrackForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            "quiz:admin_track_list"
        )

    return render(
        request,
        "quiz/student/subscription/track_form.html",
        {
            "form": form,
            "mode": "create",
        },
    )


@staff_member_required
def admin_track_update(
    request,
    pk,
):

    track = get_object_or_404(
        ExamTrack,
        pk=pk,
    )

    form = TrackForm(
        request.POST or None,
        instance=track,
    )

    if form.is_valid():

        form.save()

        return redirect(
            "quiz:admin_track_list"
        )

    return render(
        request,
        "quiz/student/subscription/track_form.html",
        {
            "form": form,
            "mode": "edit",
        },
    )


@staff_member_required
def admin_track_delete(
    request,
    pk,
):

    track = get_object_or_404(
        ExamTrack,
        pk=pk,
    )

    track.delete()

    return redirect(
        "quiz:admin_track_list"
    )


# ============================================================
# COUPONS
# ============================================================

@staff_member_required
def admin_coupon_list(request):

    coupons = (
        Coupon.objects
        .order_by("-created_at")
    )

    return render(
        request,
        "quiz/student/subscription/coupon_list.html",
        {
            "coupons": coupons,
        },
    )


@staff_member_required
def admin_coupon_create(request):

    form = CouponForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            "quiz:admin_coupon_list"
        )

    return render(
        request,
        "quiz/student/subscription/coupon_form.html",
        {
            "form": form,
        },
    )


# ============================================================
# PAYMENTS - NEW ARCHITECTURE
# ============================================================

@staff_member_required
def admin_payment_list(request):

    payments = (
        Payment.objects
        .select_related(
            "user",
            "organization",
            "subscription",
            "subscription__plan",
        )
        .order_by("-created_at")
    )

    context = {

        "payments": payments,

        "users": (
            User.objects
            .filter(is_active=True)
            .order_by("username")
        ),

        "exams": Exam.objects.all(),

        "tracks": ExamTrack.objects.all(),

        "plans": (
            SubscriptionPlan.objects
            .filter(is_active=True)
            .order_by("price", "name")
        ),

        "coupons": (
            Coupon.objects
            .filter(is_active=True)
        ),
    }

    return render(
        request,
        "quiz/student/subscription/payment_list.html",
        context,
    )


# ============================================================
# TOGGLE EXAM PUBLISH STATUS
# ============================================================

@staff_member_required
@require_POST
def toggle_exam_publish(request):

    exam_id = request.POST.get(
        "exam_id"
    )

    try:

        exam = Exam.objects.get(
            id=exam_id
        )

        exam.is_published = (
            not exam.is_published
        )

        exam.save(
            update_fields=[
                "is_published",
            ]
        )

        return JsonResponse(
            {
                "success": True,
                "is_published": (
                    exam.is_published
                ),
            }
        )

    except Exam.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Exam not found",
            },
            status=404,
        )


# ============================================================
# ADMIN: MANUAL PAYMENT
# ============================================================

@staff_member_required
@require_POST
@transaction.atomic
def admin_add_manual_payment(request):

    try:

        user_id = request.POST.get(
            "user_id"
        )

        exam_id = request.POST.get(
            "exam_id"
        )

        track_id = request.POST.get(
            "track_id"
        )

        plan_id = request.POST.get(
            "plan_id"
        )

        reference_id = request.POST.get(
            "reference_id",
            "",
        )

        if not user_id:

            return JsonResponse(
                {
                    "success": False,
                    "error": "User is required",
                },
                status=400,
            )

        if exam_id and track_id:

            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Select either Exam or Track, "
                        "not both"
                    ),
                },
                status=400,
            )

        if not exam_id and not track_id:

            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Exam or Track is required"
                    ),
                },
                status=400,
            )

        user = get_object_or_404(
            User,
            id=user_id,
        )

        exam = None
        track = None

        if exam_id:

            exam = get_object_or_404(
                Exam,
                id=exam_id,
            )

        if track_id:

            track = get_object_or_404(
                ExamTrack,
                id=track_id,
            )

        plan = get_object_or_404(
            SubscriptionPlan,
            id=plan_id,
            is_active=True,
        )

        # ----------------------------------------------------
        # AMOUNT
        # ----------------------------------------------------

        amount = Decimal(
            plan.price or 0
        )

        # ----------------------------------------------------
        # SUBSCRIPTION
        # ----------------------------------------------------

        if exam:

            subscription, entitlement = (
                SubscriptionService.create_or_reactivate_subscription(
                    user=user,
                    resource_type=RESOURCE_EXAM,
                    resource=exam,
                    plan=plan,
                    granted_by=request.user,
                    notes=(
                        "Admin manual exam payment"
                    ),
                )
            )

        else:

            subscription, entitlement = (
                SubscriptionService.create_or_reactivate_subscription(
                    user=user,
                    resource_type=RESOURCE_TRACK,
                    resource=track,
                    plan=plan,
                    granted_by=request.user,
                    notes=(
                        "Admin manual track payment"
                    ),
                )
            )

        # ----------------------------------------------------
        # UPDATE BILLING
        # ----------------------------------------------------

        subscription.amount = amount
        subscription.currency = plan.currency
        subscription.payment_status = "paid"
        subscription.payment_id = reference_id or ""
        subscription.subscribed_by_admin = True
        subscription.granted_by = request.user

        subscription.save(
            update_fields=[
                "amount",
                "currency",
                "payment_status",
                "payment_id",
                "subscribed_by_admin",
                "granted_by",
                "updated_at",
            ]
        )

        # ----------------------------------------------------
        # PAYMENT RECORD
        # ----------------------------------------------------

        payment = Payment.objects.create(
            subscription=subscription,
            amount=amount,
            currency=plan.currency,
            status=Payment.STATUS_SUCCESS,
            provider=Payment.PROVIDER_MANUAL,
            transaction_id=reference_id or "",
            order_id="",
            user=user,
            organization=None,
            paid_at=timezone.now(),
            notes="Admin manual payment",
        )

        # ----------------------------------------------------
        # RESOURCE ACCESS
        # ----------------------------------------------------

        if exam:

            AccessService.grant_access(
                user=user,
                resource_type=RESOURCE_EXAM,
                resource=exam,
                source=ResourceAccess.SOURCE_ADMIN,
                subscription=subscription,
                expires_at=subscription.expires_at,
            )

        else:

            AccessService.grant_access(
                user=user,
                resource_type=RESOURCE_TRACK,
                resource=track,
                source=ResourceAccess.SOURCE_ADMIN,
                subscription=subscription,
                expires_at=subscription.expires_at,
            )

        return JsonResponse(
            {
                "success": True,
                "payment_id": payment.id,
                "subscription_id": subscription.id,
                "entitlement_id": entitlement.id,
            }
        )

    except Exception as exc:

        logger.exception(
            "Manual payment failed"
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )

