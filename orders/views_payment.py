from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from orders.adapters.dummy import DummyPaymentAdapter
from orders.models import Order, OrderPayment
from orders.services.order_workflow_service import OrderWorkflowService


def is_dummy_payment_allowed(user):
    """
    Public online payments are strictly disabled in production during Day-1 release.
    Dummy adapter payment simulation can only be executed by staff or when
    ENABLE_DUMMY_PAYMENT_GATEWAY is explicitly enabled in settings.
    """
    return bool(user.is_staff or getattr(settings, "ENABLE_DUMMY_PAYMENT_GATEWAY", False))


@login_required
def initiate_online_payment(request, order_number):
    """
    Initiates payment with the provider-independent payment adapter (Dummy adapter for MVP).
    Redirects customer to simulated gateway return URL.
    Restricted to authorized test environments and staff.
    """
    if not is_dummy_payment_allowed(request.user):
        raise PermissionDenied("Online payments are currently disabled for public orders.")

    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.online_payment_status == Order.ONLINE_STATUS_PAID:
        messages.info(request, "This order has already been paid.")
        return redirect("orders:customer_order_detail", order_number=order.order_number)

    payment = order.payments.first()
    if not payment:
        payment = OrderPayment.objects.create(
            order=order,
            payment_method=Order.PAYMENT_METHOD_ONLINE,
            amount=order.grand_total,
            currency=order.currency,
            status=OrderPayment.STATUS_PENDING,
            gateway_name="dummy",
            idempotency_key=f"PAY-{order.order_number}",
        )

    adapter = DummyPaymentAdapter()
    callback_url = request.build_absolute_uri(
        reverse("orders:payment_callback", kwargs={"order_number": order.order_number})
    )

    init_res = adapter.initiate_payment(payment, return_url=callback_url)
    redirect_url = init_res.get("redirect_url")

    return redirect(redirect_url)


@login_required
def payment_callback(request, order_number):
    """
    Handles payment callback from gateway.
    Verifies payload and idempotently confirms order payment.
    Public access is blocked: client-controlled mock parameters cannot mark orders paid.
    """
    if not is_dummy_payment_allowed(request.user):
        raise PermissionDenied("Simulated payment confirmation cannot be used for public orders.")

    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    payment = order.payments.first()

    if not payment:
        messages.error(request, "Payment record not found.")
        return redirect("orders:customer_order_detail", order_number=order.order_number)

    adapter = DummyPaymentAdapter()
    verification = adapter.verify_payment(request.GET.dict())

    if verification.get("is_successful"):
        OrderWorkflowService.confirm_online_payment(
            payment,
            gateway_payment_id=verification.get("gateway_payment_id"),
            raw_response=verification.get("raw_response"),
        )
        messages.success(request, f"Payment verified! Order #{order.order_number} is now confirmed and processing.")
    else:
        payment.status = OrderPayment.STATUS_FAILED
        payment.save(update_fields=["status", "updated_at"])
        messages.error(request, "Payment was not successful. You may retry your payment below.")

    return redirect("orders:customer_order_detail", order_number=order.order_number)
