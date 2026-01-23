from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from quiz.models import *
from quiz.services.payment_service import PaymentService


from quiz.services.subscription_guard import has_active_track_subscription

from quiz.services.subscription_service import SubscriptionService
from quiz.services.access import has_active_track_subscription

@login_required
@require_POST
def subscribe_track(request, track_id):
    track = get_object_or_404(ExamTrack, id=track_id, is_active=True)

    # 🚫 BLOCK paid tracks
    if track.subscription_plans.filter(is_active=True).exists():
        messages.error(
            request,
            "This track requires a paid subscription. Please contact admin."
        )
        return redirect("quiz:exam_list")

    # ✅ FREE FLOW
    ExamTrackSubscription.objects.update_or_create(
        user=request.user,
        track=track,
        defaults={
            "is_active": True,
            "payment_required": False,
            "amount": 0,
            "expires_at": None,
        }
    )

    messages.success(request, "Subscribed successfully!")
    return redirect("quiz:student_dashboard")




from quiz.services.access import has_active_track_subscription


@login_required
def subscribe_track_checkout(request, track_id):
    track = get_object_or_404(ExamTrack, id=track_id, is_active=True)

    if has_valid_subscription(request.user, track=track):
        messages.info(request, "You already have an active subscription.")
        return redirect("quiz:student_dashboard")

    plans = track.subscription_plans.filter(is_active=True)

    if not plans.exists():
        messages.error(request, "No subscription plans available for this track.")
        return redirect("quiz:exam_list")

    return render(request, "quiz/checkout.html", {
        "track": track,
        "plans": plans,
    })


@login_required
def subscription_history(request):
    track_subs = (
        ExamTrackSubscription.objects
        .filter(user=request.user)
        .select_related("track")
        .order_by("-subscribed_at")
    )

    exam_subs = (
        ExamSubscription.objects
        .filter(user=request.user)
        .select_related("exam")
        .order_by("-subscribed_at")
    )

    payments = (
        PaymentRecord.objects
        .filter(user=request.user)
        .select_related("track", "exam")
        .order_by("-paid_at")
    )

    return render(
        request,
        "quiz/subscription/history.html",
        {
            "track_subs": track_subs,
            "exam_subs": exam_subs,
            "payments": payments,
            "now": timezone.now(),
        }
    )






from quiz.services.subscription_guard import has_active_exam_subscription
@login_required
@require_POST
def subscribe_exam(request, exam_id):
    exam = get_object_or_404(
        Exam,
        id=exam_id,
        is_published=True
    )

    # 🔒 Guard: already subscribed
    existing = ExamSubscription.objects.filter(
        user=request.user,
        exam=exam,
        is_active=True
    ).first()

    if existing and existing.is_valid():
        messages.info(request, "You already have access to this exam.")
        return redirect("quiz:exam_list")

    try:
        PaymentService.apply_manual_payment(
            user=request.user,
            exam=exam,
            track=None,
            coupon=None,
            reference_id="user_free_exam" if exam.is_free else "user_paid_exam"
        )
    except Exception as e:
        messages.error(request, str(e))
        return redirect("quiz:exam_list")

    messages.success(request, "Exam unlocked successfully 🎉")
    return redirect("quiz:exam_list")






@login_required
@require_POST
def finalize_track_subscription(request, track_id):
    """
    Final step after checkout
    Applies coupon, records payment, grants access
    """

    track = get_object_or_404(
        ExamTrack,
        id=track_id,
        is_active=True
    )

    coupon_code = request.POST.get("coupon", "").strip().upper()

    try:
        PaymentService.apply_manual_payment(
            user=request.user,
            track=track,
            coupon=coupon_code and None,  # real coupon object resolved in service
            reference_id="USER_CHECKOUT",
        )
    except Exception as e:
        messages.error(request, str(e))
        return redirect("quiz:subscribe_track_checkout", track_id=track.id)

    messages.success(request, "Subscription activated successfully.")
    return redirect("quiz:student_dashboard")



@login_required
@require_POST
def log_enrollment_lead(request):
    """
    Logs interest for paid items
    """

    item_type = request.POST.get("type")   # exam / track
    item_id = request.POST.get("item_id")

    if item_type not in ("exam", "track"):
        return JsonResponse({"ok": False}, status=400)

    return JsonResponse({"ok": True})


from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def track_checkout(request, track_id):
    track = get_object_or_404(ExamTrack, id=track_id, is_active=True)

    # 🔐 Guard: already subscribed
    if has_active_track_subscription(request.user, track):
        messages.info(request, "You already have access to this track.")
        return redirect("quiz:student_dashboard")

    plans = track.subscription_plans.filter(is_active=True)

    if not plans.exists():
        messages.error(request, "No pricing plans available for this track.")
        return redirect("quiz:exam_list")

    # ================= POST HANDLING =================
    if request.method == "POST":
        plan_id = request.POST.get("plan_id")
        coupon_code = request.POST.get("coupon")
        action = request.POST.get("action", "subscribe")

        if not plan_id:
            messages.error(request, "Please select a subscription plan.")
            return redirect(request.path)

        plan = get_object_or_404(plans, id=plan_id)

        # 🔍 DEBUG (remove later)
        print("TRACK:", track)
        print("PLAN:", plan)
        print("ACTION:", action)
        print("COUPON:", coupon_code)

        # 🚀 TODO: create subscription / payment intent
        messages.success(
            request,
            f"You selected the '{plan.name}' plan. Proceeding to payment."
        )

        return redirect("quiz:student_dashboard")  # or payment page

    # ================= GET =================
    return render(request, "quiz/checkout.html", {
        "track": track,
        "plans": plans,
        "action": request.GET.get("action", "subscribe"),
    })



from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404

from quiz.models import ExamTrack, SubscriptionPlan


@staff_member_required
def get_track_plans(request, track_id):
    """
    AJAX: Return active plans for a track
    """
    track = get_object_or_404(ExamTrack, id=track_id, is_active=True)

    plans = track.subscription_plans.filter(is_active=True)

    data = [
        {
            "id": plan.id,
            "name": plan.name,
            "price": str(plan.price),
            "duration_days": plan.duration_days,
        }
        for plan in plans
    ]

    return JsonResponse({"plans": data})
