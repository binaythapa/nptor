import logging
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from courses.models import Course
from organizations.models import ResourceAccess
from quiz.models import Coupon, ExamTrack
from quiz.models.payment_record import PaymentRecord
from subscriptions.models import SubscriptionPlan
from subscriptions.services.plan_service import get_plan_for_course, get_plan_for_track
from subscriptions.services.subscription_service import SubscriptionService

User = get_user_model()
logger = logging.getLogger(__name__)


@staff_member_required
def admin_payment_list(request):
    payments = PaymentRecord.objects.select_related("user", "course", "track", "subscription_plan").order_by("-paid_at")
    return render(request, "quiz/student/subscription/payment_list.html", {
        "payments": payments,
        "users": User.objects.filter(is_active=True).order_by("username"),
        "courses": Course.objects.filter(is_published=True).order_by("title"),
        "tracks": ExamTrack.objects.filter(is_active=True).order_by("title"),
        "plans": SubscriptionPlan.objects.filter(is_active=True).order_by("scope", "price", "name"),
        "coupons": Coupon.objects.filter(is_active=True),
    })


@staff_member_required
@require_POST
@transaction.atomic
def admin_add_manual_payment(request):
    user = get_object_or_404(User, id=request.POST.get("user_id"))
    purchase_type = (request.POST.get("purchase_type") or "").strip()
    course_id = request.POST.get("course_id")
    track_id = request.POST.get("track_id")
    plan_id = request.POST.get("plan_id")
    reference_id = (request.POST.get("reference_id") or "").strip()
    payment_method = (request.POST.get("payment_method") or PaymentRecord.PAYMENT_OTHER).strip()

    if purchase_type not in {"course", "track", "subscription"}:
        return JsonResponse({"success": False, "error": "Select Course, Track, or All-access Subscription."}, status=400)
    if payment_method not in dict(PaymentRecord.PAYMENT_METHOD_CHOICES):
        return JsonResponse({"success": False, "error": "Invalid payment method."}, status=400)

    course = get_object_or_404(Course, id=course_id) if purchase_type == "course" else None
    track = get_object_or_404(ExamTrack, id=track_id) if purchase_type == "track" else None
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True) if plan_id else None

    if purchase_type == "course":
        plan = plan or get_plan_for_course(course)
        if not plan or plan.scope != SubscriptionPlan.SCOPE_RESOURCE:
            return JsonResponse({"success": False, "error": "Select a valid course plan."}, status=400)
        resource_type, resource = "course", course
    elif purchase_type == "track":
        plan = plan or get_plan_for_track(track)
        if not plan or plan.scope != SubscriptionPlan.SCOPE_RESOURCE:
            return JsonResponse({"success": False, "error": "Select a valid track plan."}, status=400)
        resource_type, resource = "track", track
    else:
        if not plan or not plan.is_all_access():
            return JsonResponse({"success": False, "error": "Select an all-access subscription plan."}, status=400)
        resource_type = resource = None

    if purchase_type in {"course", "track"}:
        subscription, entitlement = SubscriptionService.create_or_reactivate_subscription(
            user=user,
            resource_type=resource_type,
            resource=resource,
            plan=plan,
            granted_by=request.user,
            notes="Admin manual payment",
        )
        from subscriptions.services.access_service import AccessService
        AccessService.grant_access(
            user=user,
            resource_type=resource_type,
            resource=resource,
            source=ResourceAccess.SOURCE_ADMIN,
            subscription=subscription,
            expires_at=subscription.expires_at,
        )
    else:
        subscription = SubscriptionService.create_subscription(
            plan=plan,
            user=user,
            organization=None,
            granted_by=request.user,
            subscribed_by_admin=True,
            payment_status="paid",
            order_id="",
            notes="Admin manual all-access subscription",
            start_at=timezone.now(),
        )
        entitlement = None

    subscription.amount = Decimal(plan.price or 0)
    subscription.currency = plan.currency
    subscription.payment_status = "paid"
    subscription.payment_id = reference_id
    subscription.subscribed_by_admin = True
    subscription.granted_by = request.user
    subscription.save(update_fields=["amount", "currency", "payment_status", "payment_id", "subscribed_by_admin", "granted_by", "updated_at"])

    record = PaymentRecord.objects.create(
        user=user,
        course=course,
        track=track,
        subscription_plan=plan,
        amount=plan.price,
        currency=plan.currency,
        payment_method=payment_method,
        reference_id=reference_id,
        remarks="Admin manual payment",
        created_by_admin=True,
    )

    return JsonResponse({
        "success": True,
        "payment_id": record.id,
        "subscription_id": subscription.id,
        "entitlement_id": entitlement.id if entitlement else None,
    })
