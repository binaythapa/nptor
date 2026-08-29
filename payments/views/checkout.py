# payments/views/checkout.py

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect

from courses.models import Course
from quiz.models import Exam, ExamTrack

from organizations.models import ResourceAccess

from payments.models import PaymentOrder
from payments.services import (
    OrderService,
    PaymentService,
)

from subscriptions.services import AccessService


# ============================================================
# CONFIGURATION
# ============================================================

# Keep Dummy while developing/testing.
#
# Later:
#
# PAYMENT_GATEWAY = "razorpay"
#
# This can eventually come from Django settings.

DEFAULT_GATEWAY = "dummy"


# ============================================================
# COMMON PAYMENT STARTER
# ============================================================

def _start_payment(
    *,
    request,
    resource_type,
    resource,
    amount,
    currency="INR",
):
    """
    Common payment initialization for:

        Course
        Track
        Exam

    Flow:

        Resource
            ↓
        PaymentOrder
            ↓
        PaymentTransaction
            ↓
        Payment Gateway
    """

    # --------------------------------------------------------
    # Validate amount
    # --------------------------------------------------------

    try:
        amount = Decimal(str(amount or 0))
    except (TypeError, ValueError):
        messages.error(
            request,
            "Invalid payment amount.",
        )

        return redirect(
            "quiz:exam_list"
        )

    if amount < Decimal("0"):
        messages.error(
            request,
            "Invalid payment amount.",
        )

        return redirect(
            "quiz:exam_list"
        )

    # --------------------------------------------------------
    # Create PaymentOrder
    # --------------------------------------------------------

    try:

        order = OrderService.create_order(
            user=request.user,
            resource_type=resource_type,
            resource=resource,
            amount=amount,
            currency=currency,
        )

    except ValidationError as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "quiz:exam_list"
        )

    # --------------------------------------------------------
    # Initiate gateway
    # --------------------------------------------------------

    try:

        result = PaymentService.initiate_payment(
            order=order,
            gateway_name=DEFAULT_GATEWAY,
        )

    except Exception as exc:

        messages.error(
            request,
            f"Unable to start payment: {exc}",
        )

        return redirect(
            "quiz:exam_list"
        )

    # --------------------------------------------------------
    # Gateway initialization failed
    # --------------------------------------------------------

    if not result.get("success"):

        gateway_response = result.get(
            "gateway_response",
            {},
        )

        messages.error(
            request,
            gateway_response.get(
                "error",
                "Unable to initialize payment.",
            ),
        )

        return redirect(
            "quiz:exam_list"
        )

    # --------------------------------------------------------
    # Gateway response
    # --------------------------------------------------------

    gateway_response = result.get(
        "gateway_response",
        {}
    )

    payment_url = gateway_response.get(
        "payment_url"
    )

    # --------------------------------------------------------
    # Real gateway
    #
    # Razorpay / Stripe/etc. can return a hosted
    # payment URL.
    # --------------------------------------------------------

    if payment_url:

        return redirect(
            payment_url
        )

    # --------------------------------------------------------
    # Dummy/local gateway
    # --------------------------------------------------------

    return redirect(
        "payments:payment_checkout",
        order_number=order.order_number,
    )


# ============================================================
# COURSE CHECKOUT
# ============================================================

@login_required
def course_checkout(
    request,
    course_id,
):
    """
    Start checkout for a Course.
    """

    course = get_object_or_404(
        Course,
        pk=course_id,
    )

    # --------------------------------------------------------
    # Existing access
    # --------------------------------------------------------

    if AccessService.has_access(
        student=request.user,
        resource_type=(
            AccessService.RESOURCE_COURSE
        ),
        resource=course,
    ):

        messages.info(
            request,
            "You already have access to this course.",
        )

        return redirect(
            "quiz:exam_list"
        )

    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    amount = (
        getattr(
            course,
            "price",
            0,
        )
        or 0
    )

    currency = (
        getattr(
            course,
            "currency",
            None,
        )
        or "INR"
    )

    # --------------------------------------------------------
    # Free course
    # --------------------------------------------------------

    if Decimal(str(amount)) == Decimal("0"):

        messages.info(
            request,
            "This course is free.",
        )

        return redirect(
            "quiz:exam_list"
        )

    # --------------------------------------------------------
    # Start payment
    # --------------------------------------------------------

    return _start_payment(
        request=request,
        resource_type=(
            PaymentOrder.RESOURCE_COURSE
        ),
        resource=course,
        amount=amount,
        currency=currency,
    )


# ============================================================
# TRACK CHECKOUT
# ============================================================

@login_required
def track_checkout(
    request,
    track_id,
):
    """
    Start checkout for an ExamTrack.
    """

    track = get_object_or_404(
        ExamTrack,
        pk=track_id,
        is_active=True,
    )

    # --------------------------------------------------------
    # Existing Track access
    # --------------------------------------------------------

    if AccessService.has_access(
        student=request.user,
        resource_type=(
            AccessService.RESOURCE_TRACK
        ),
        resource=track,
    ):

        messages.info(
            request,
            "You already have access to this track.",
        )

        return redirect(
            "quiz:exam_list"
        )

    # --------------------------------------------------------
    # Find subscription plan
    # --------------------------------------------------------
    # --------------------------------------------------------
    # Find subscription plan
    # --------------------------------------------------------

    from subscriptions.services.plan_service import (
        get_plan_for_track,
    )

    plan = get_plan_for_track(
        track,
        None,
    )

    if not plan:

        messages.error(
            request,
            "No subscription plan is available for this track.",
        )

        return redirect(
            "quiz:exam_list"
        )

    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    amount = (
        plan.price
        or 0
    )

    currency = (
        plan.currency
        or "INR"
    )

    # --------------------------------------------------------
    # Free track
    # --------------------------------------------------------

    if Decimal(str(amount)) == Decimal("0"):

        messages.info(
            request,
            "This track is free.",
        )

        return redirect(
            "quiz:exam_list"
        )

    # --------------------------------------------------------
    # Start payment
    # --------------------------------------------------------

    return _start_payment(
        request=request,
        resource_type=(
            PaymentOrder.RESOURCE_TRACK
        ),
        resource=track,
        amount=amount,
        currency=currency,
    )


# ============================================================
# EXAM CHECKOUT
# ============================================================

@login_required
def exam_checkout(
    request,
    exam_id,
):
    """
    Start checkout for an individual Exam.

    Important:

    Track access is intentionally respected here.

    If the student already owns the Track containing
    this Exam, the student must NOT purchase the Exam again.
    """

    exam = get_object_or_404(
        Exam,
        pk=exam_id,
        is_published=True,
    )

    # --------------------------------------------------------
    # Existing effective access
    #
    # This checks:
    #
    # 1. Direct Exam access
    # 2. Track inherited access
    # --------------------------------------------------------

    if AccessService.has_access(
        student=request.user,
        resource_type=(
            AccessService.RESOURCE_EXAM
        ),
        resource=exam,
    ):

        messages.info(
            request,
            "You already have access to this exam.",
        )

        return redirect(
            "quiz:exam_start",
            exam_id=exam.id,
        )

    # --------------------------------------------------------
    # Free exam
    # --------------------------------------------------------

    if exam.is_free:

        messages.info(
            request,
            "This exam is free.",
        )

        return redirect(
            "quiz:exam_start",
            exam_id=exam.id,
        )

    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    amount = (
        getattr(
            exam,
            "price",
            0,
        )
        or 0
    )

    currency = (
        getattr(
            exam,
            "currency",
            None,
        )
        or "INR"
    )

    # --------------------------------------------------------
    # Zero-price exam
    # --------------------------------------------------------

    if Decimal(str(amount)) == Decimal("0"):

        messages.info(
            request,
            "This exam does not require payment.",
        )

        return redirect(
            "quiz:exam_start",
            exam_id=exam.id,
        )

    # --------------------------------------------------------
    # Start individual exam payment
    # --------------------------------------------------------

    return _start_payment(
        request=request,
        resource_type=(
            PaymentOrder.RESOURCE_EXAM
        ),
        resource=exam,
        amount=amount,
        currency=currency,
    )