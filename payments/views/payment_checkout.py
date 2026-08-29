# payments/views/payment_checkout.py

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import (
    get_object_or_404,
    render,
    redirect,
)

from payments.models import (
    PaymentOrder,
    PaymentTransaction,
)


@login_required
def payment_checkout(
    request,
    order_number,
):
    """
    Display the payment checkout page.

    Used by the Dummy gateway during local development.

    This view does NOT grant access.
    """

    # ---------------------------------------------------------
    # Get order belonging to current user
    # ---------------------------------------------------------

    order = get_object_or_404(
        PaymentOrder,
        order_number=order_number,
        user=request.user,
    )

    # ---------------------------------------------------------
    # Already paid
    # ---------------------------------------------------------

    if order.status == PaymentOrder.STATUS_PAID:

        return redirect(
            "payments:payment_success",
            order_number=order.order_number,
        )

    # ---------------------------------------------------------
    # Get latest transaction
    # ---------------------------------------------------------

    transaction_obj = (
        PaymentTransaction.objects
        .filter(
            order=order,
        )
        .order_by("-created_at")
        .first()
    )

    if not transaction_obj:

        raise ValidationError(
            "No payment transaction exists for this order."
        )

    # ---------------------------------------------------------
    # Render checkout
    # ---------------------------------------------------------

    return render(
        request,
        "payments/payment_checkout.html",
        {
            "order": order,
            "transaction": transaction_obj,
            "resource": order.get_resource(),
        },
    )