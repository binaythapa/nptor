from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme

from courses.models import Course
from quiz.models import Exam, ExamTrack
from payments.models import PaymentOrder
from payments.services import OrderService, PaymentService
from subscriptions.services import AccessService
from subscriptions.services.plan_service import (
    get_plan_for_course,
    get_plan_for_exam,
    get_plan_for_track,
)

DEFAULT_GATEWAY = "dummy"
PAYMENT_RETURN_SESSION_KEY = "payment_return_to"


def _safe_return_url(request, value):
    if not value:
        return None
    if not value.startswith("/") or value.startswith("//"):
        return None
    if not url_has_allowed_host_and_scheme(
        value,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return None
    return value


def _start_payment(*, request, resource_type, resource, amount, currency="INR", return_to=None):
    safe_return = _safe_return_url(request, return_to)
    if safe_return:
        request.session[PAYMENT_RETURN_SESSION_KEY] = safe_return

    try:
        order = OrderService.create_order(
            user=request.user,
            resource_type=resource_type,
            resource=resource,
            amount=amount,
            currency=currency,
        )
    except ValidationError as exc:
        messages.error(request, str(exc))
        return redirect("quiz:exam_list")

    try:
        result = PaymentService.initiate_payment(
            order=order,
            gateway_name=DEFAULT_GATEWAY,
        )
    except Exception:
        messages.error(request, "Unable to start payment. Please try again.")
        return redirect("quiz:exam_list")

    if not result.get("success"):
        gateway_response = result.get("gateway_response") or {}
        messages.error(
            request,
            gateway_response.get("error", "Unable to initialize payment."),
        )
        return redirect("quiz:exam_list")

    gateway_response = result.get("gateway_response") or {}
    payment_url = gateway_response.get("payment_url")
    if payment_url:
        return redirect(payment_url)

    return redirect(
        "payments:payment_checkout",
        order_number=order.order_number,
    )


@login_required
def course_checkout(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    if not course.is_publicly_available():
        messages.error(request, "This course is not currently available for purchase.")
        return redirect("quiz:exam_list")

    if AccessService.has_access(
        student=request.user,
        resource_type=AccessService.RESOURCE_COURSE,
        resource=course,
    ):
        messages.info(request, "You already have access to this course.")
        return redirect("quiz:exam_list")

    plan = get_plan_for_course(course)
    if not plan:
        messages.error(request, "No subscription plan is available for this course.")
        return redirect("quiz:exam_list")

    if plan.price == 0:
        messages.info(request, "This course is free.")
        return redirect("quiz:exam_list")

    return _start_payment(
        request=request,
        resource_type=PaymentOrder.RESOURCE_COURSE,
        resource=course,
        amount=plan.price,
        currency=plan.currency,
        return_to=request.GET.get("next"),
    )


@login_required
def track_checkout(request, track_id):
    track = get_object_or_404(ExamTrack, pk=track_id, is_active=True)

    if AccessService.has_access(
        student=request.user,
        resource_type=AccessService.RESOURCE_TRACK,
        resource=track,
    ):
        messages.info(request, "You already have access to this track.")
        return redirect("quiz:exam_list")

    plan = get_plan_for_track(track)
    if not plan:
        messages.error(request, "No subscription plan is available for this track.")
        return redirect("quiz:exam_list")

    if plan.price == 0:
        messages.info(request, "This track is free.")
        return redirect("quiz:exam_list")

    return _start_payment(
        request=request,
        resource_type=PaymentOrder.RESOURCE_TRACK,
        resource=track,
        amount=plan.price,
        currency=plan.currency,
        return_to=request.GET.get("next"),
    )


@login_required
def exam_checkout(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id, is_published=True)

    if AccessService.has_access(
        student=request.user,
        resource_type=AccessService.RESOURCE_EXAM,
        resource=exam,
    ):
        messages.info(request, "You already have direct access to this exam.")
        return redirect("quiz:exam_start", exam_id=exam.id)

    plan = get_plan_for_exam(exam)
    if not plan:
        messages.error(
            request,
            "This exam has no direct purchase plan. Access it through an eligible track.",
        )
        return redirect("quiz:exam_detail", exam_id=exam.id)

    if plan.price == 0:
        messages.info(request, "This exam is free.")
        return redirect("quiz:exam_start", exam_id=exam.id)

    return _start_payment(
        request=request,
        resource_type=PaymentOrder.RESOURCE_EXAM,
        resource=exam,
        amount=plan.price,
        currency=plan.currency,
        return_to=request.GET.get("next"),
    )
