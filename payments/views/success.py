# payments/views/success.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from payments.models import PaymentOrder


@login_required
def payment_success(
    request,
    order_number,
):
    """
    Display a successful payment only after the order is paid.

    Access/subscription is fulfilled before this page is reached.
    """

    order = get_object_or_404(
        PaymentOrder,
        order_number=order_number,
        user=request.user,
    )

    if order.status != PaymentOrder.STATUS_PAID:
        messages.info(
            request,
            "This payment has not been completed yet.",
        )
        return redirect(
            "payments:payment_checkout",
            order_number=order.order_number,
        )

    return render(
        request,
        "payments/payment_success.html",
        {
            "order": order,
            "resource": order.get_resource(),
        },
    )
