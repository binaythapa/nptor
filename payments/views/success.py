# payments/views/success.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from payments.models import PaymentOrder


@login_required
def payment_success(
    request,
    order_number,
):
    """
    Display successful payment result.

    Access/subscription should already have been fulfilled
    before this page is reached.
    """

    order = get_object_or_404(
        PaymentOrder,
        order_number=order_number,
        user=request.user,
    )

    return render(
        request,
        "payments/payment_success.html",
        {
            "order": order,
            "resource": order.get_resource(),
        },
    )