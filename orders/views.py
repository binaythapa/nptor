from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from orders.models import DigitalDelivery, Order, SubOrder, OrderReturnRequest
from orders.services.order_workflow_service import OrderWorkflowService
from vendors.permissions import get_vendor_profile


@login_required
def customer_order_detail(request, order_number):
    """
    Customer order detail view.
    Enforces tenant access control: customers can ONLY access their own orders.
    Displays payment actions, package tracking, and active digital download links.
    """
    order = get_object_or_404(
        Order.objects.select_related("shipping_address")
        .prefetch_related("suborders", "suborders__items", "suborders__vendor"),
        order_number=order_number,
        user=request.user,
    )

    # Fetch digital delivery grants for this order
    digital_deliveries = []
    if order.online_payment_status == Order.ONLINE_STATUS_PAID:
        digital_deliveries = (
            DigitalDelivery.objects
            .filter(order_item__suborder__master_order=order, user=request.user, is_revoked=False)
            .select_related("digital_asset", "order_item")
        )

    return render(
        request,
        "orders/customer_order_detail.html",
        {
            "order": order,
            "digital_deliveries": digital_deliveries,
        },
    )


@login_required
def vendor_suborder_detail(request, suborder_number):
    """
    Vendor suborder detail view.
    Enforces tenant isolation: sellers can ONLY access their own SubOrders.
    Allows sellers to update fulfillment status (e.g. ship with tracking).
    """
    profile = get_vendor_profile(request.user)
    if not profile:
        raise PermissionDenied("You do not have an active seller profile.")

    suborder = get_object_or_404(
        SubOrder.objects.select_related("master_order", "master_order__shipping_address")
        .prefetch_related("items", "items__variant"),
        suborder_number=suborder_number,
        vendor=profile,
    )

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "ship":
            carrier = request.POST.get("carrier", "").strip()
            tracking_number = request.POST.get("tracking_number", "").strip()
            try:
                OrderWorkflowService.update_suborder_fulfillment(
                    suborder,
                    new_status=SubOrder.FULFILLMENT_SHIPPED,
                    carrier=carrier,
                    tracking_number=tracking_number,
                )
                messages.success(request, f"Suborder {suborder.suborder_number} marked as shipped.")
            except ValidationError as exc:
                messages.error(request, str(exc))
        elif action == "deliver":
            try:
                OrderWorkflowService.update_suborder_fulfillment(
                    suborder,
                    new_status=SubOrder.FULFILLMENT_DELIVERED,
                )
                messages.success(request, f"Suborder {suborder.suborder_number} marked as delivered.")
            except ValidationError as exc:
                messages.error(request, str(exc))
        return redirect("orders:vendor_suborder_detail", suborder_number=suborder.suborder_number)

    return render(
        request,
        "orders/vendor_suborder_detail.html",
        {"suborder": suborder, "profile": profile},
    )


@login_required
def vendor_suborder_list(request):
    """
    Vendor order fulfillment queue.
    Scoped strictly to the requesting vendor's suborders.
    """
    profile = get_vendor_profile(request.user)
    if not profile:
        raise PermissionDenied("You do not have an active seller profile.")

    status_filter = request.GET.get("status")
    qs = SubOrder.objects.filter(vendor=profile).select_related("master_order").order_by("-created_at")
    if status_filter:
        qs = qs.filter(fulfillment_status=status_filter)

    return render(
        request,
        "orders/vendor_suborder_list.html",
        {"suborders": qs, "profile": profile, "status_filter": status_filter},
    )


@staff_member_required
def admin_order_list(request):
    """
    Staff master order overview for platform administration.
    """
    orders = (
        Order.objects
        .select_related("user", "shipping_address")
        .prefetch_related("suborders", "suborders__vendor")
        .order_by("-created_at")
    )
    status_filter = request.GET.get("status")
    if status_filter:
        orders = orders.filter(order_status=status_filter)

    return render(
        request,
        "orders/admin_order_list.html",
        {
            "orders": orders,
            "status_filter": status_filter,
            "status_choices": Order.ORDER_STATUS_CHOICES,
        },
    )

@login_required
def customer_order_list(request):
    """Customer order history overview showing past orders with fulfillment timelines."""
    orders = (
        Order.objects
        .filter(user=request.user)
        .select_related("shipping_address")
        .prefetch_related("suborders", "suborders__items", "suborders__vendor")
        .order_by("-created_at")
    )
    return render(
        request,
        "orders/customer_order_list.html",
        {"orders": orders},
    )


@login_required
def customer_return_request(request, suborder_number):
    """Customer initiates a return request for a delivered suborder package."""
    suborder = get_object_or_404(
        SubOrder.objects.select_related("master_order", "vendor"),
        suborder_number=suborder_number,
        master_order__user=request.user,
    )

    if suborder.fulfillment_status != SubOrder.FULFILLMENT_DELIVERED:
        messages.warning(request, "Return requests can only be submitted for delivered packages.")
        return redirect("orders:customer_order_detail", order_number=suborder.master_order.order_number)

    if request.method == "POST":
        reason = request.POST.get("reason", OrderReturnRequest.REASON_DEFECTIVE)
        explanation = request.POST.get("explanation", "").strip()
        if not explanation:
            messages.error(request, "Please provide an explanation describing the reason for return.")
        else:
            OrderReturnRequest.objects.create(
                suborder=suborder,
                user=request.user,
                reason=reason,
                explanation=explanation,
            )
            messages.success(request, f"Return request for Package {suborder.suborder_number} submitted successfully.")
            return redirect("orders:customer_order_detail", order_number=suborder.master_order.order_number)

    return render(
        request,
        "orders/customer_return_request.html",
        {
            "suborder": suborder,
            "reasons": OrderReturnRequest.REASON_CHOICES,
        },
    )

