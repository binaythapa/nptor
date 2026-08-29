from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    get_object_or_404,
    redirect,
)

from payments.models import (
    PaymentOrder,
    PaymentTransaction,
)

from payments.services import (
    PaymentService,
    PaymentFulfillmentService,
)


@login_required
def payment_verify(
    request,
    order_number,
):
    """
    Verify and fulfill a payment.

    Used by the Dummy gateway during development.
    """

    if request.method != "POST":

        return redirect(
            "payments:payment_checkout",
            order_number=order_number,
        )

    order = get_object_or_404(
        PaymentOrder,
        order_number=order_number,
        user=request.user,
    )

    transaction_obj = (
        PaymentTransaction.objects
        .filter(
            order=order,
        )
        .order_by("-created_at")
        .first()
    )

    if not transaction_obj:

        messages.error(
            request,
            "Payment transaction not found.",
        )

        return redirect(
            "quiz:exam_list"
        )

    # ---------------------------------------------------------
    # Verify payment
    # ---------------------------------------------------------

    result = PaymentService.verify_payment(
        transaction_obj=transaction_obj,
        data=request.POST,
    )

    if not result.get("success"):

        messages.error(
            request,
            result.get(
                "gateway_response",
                {},
            ).get(
                "error",
                "Payment verification failed.",
            ),
        )

        return redirect(
            "payments:payment_checkout",
            order_number=order.order_number,
        )

    # ---------------------------------------------------------
    # Fulfill
    # ---------------------------------------------------------

    fulfillment = (
        PaymentFulfillmentService.fulfill(
            result["transaction"]
        )
    )

    if not fulfillment.get("success"):

        messages.error(
            request,
            "Payment succeeded but fulfillment failed. "
            "Please contact support.",
        )

        return redirect(
            "payments:payment_checkout",
            order_number=order.order_number,
        )

    messages.success(
        request,
        "Payment completed successfully.",
    )

    return redirect(
        "payments:payment_success",
        order_number=order.order_number,
    )