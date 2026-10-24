import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from cart.services.cart_service import (
    CartService,
    InactiveProductError,
    InsufficientStockError,
)
from orders.forms import CheckoutForm
from orders.models import Order, ShippingAddress
from orders.services.checkout_service import CheckoutService
from orders.services.order_workflow_service import OrderWorkflowService


@login_required
def checkout_view(request):
    """
    Customer checkout view:
    - Validates persistent cart and product availability.
    - Captures Nepal shipping address for physical deliveries.
    - Enforces COD rules (disabling COD for digital or non-COD products).
    - Prevents duplicate order creation using idempotency keys.
    - Atomically reserves stock and creates split master/suborders.
    """
    cart = CartService.get_or_create_cart(request)
    if not cart.items.exists():
        messages.warning(request, "Your cart is empty. Please add products before proceeding to checkout.")
        return redirect("cart:detail")

    # Server-side validation of cart state and price changes
    try:
        analysis = CartService.validate_cart(cart)
    except (InactiveProductError, ValidationError) as exc:
        messages.error(request, str(exc))
        return redirect("cart:detail")

    has_physical = analysis["has_physical"]
    is_cod_eligible = analysis["is_cod_eligible"]
    has_digital = analysis.get("has_digital", False)

    if has_digital and not (request.user.is_authenticated and request.user.is_staff):
        messages.warning(
            request,
            "Digital products are currently in preview mode during initial release. "
            "Please remove digital items from your cart to proceed with physical checkout."
        )
        return redirect("cart:detail")
    items = cart.items.select_related("variant", "variant__product", "variant__product__vendor").order_by("added_at")
    subtotal = analysis["subtotal"]

    # Prepopulate with user's most recent shipping address if available
    latest_address = ShippingAddress.objects.filter(user=request.user).order_by("-created_at").first()

    if request.method == "POST":
        form = CheckoutForm(request.POST, requires_shipping=has_physical, user=request.user)
        if form.is_valid():
            payment_method = form.cleaned_data["payment_method"]
            idempotency_key = form.cleaned_data.get("idempotency_key") or request.POST.get("idempotency_key")

            # 1. Idempotency check: if an order with this key already exists for this user, return it safely
            if idempotency_key:
                existing_order = Order.objects.filter(idempotency_key=idempotency_key, user=request.user).first()
                if existing_order:
                    messages.info(request, f"Order #{existing_order.order_number} has already been placed.")
                    return redirect("orders:customer_order_detail", order_number=existing_order.order_number)

            # 2. Server-side payment method restriction
            if payment_method == Order.PAYMENT_METHOD_COD and not is_cod_eligible:
                messages.error(request, "Cash on Delivery is not available for this cart composition.")
                return render(
                    request,
                    "orders/checkout.html",
                    {
                        "form": form,
                        "cart": cart,
                        "items": items,
                        "analysis": analysis,
                        "subtotal": subtotal,
                        "has_physical": has_physical,
                        "is_cod_eligible": is_cod_eligible,
                    },
                )

            # 3. Save shipping address for physical goods
            shipping_address = None
            if has_physical:
                shipping_address = form.save(commit=False)
                shipping_address.user = request.user
                shipping_address.country = "NP"
                shipping_address.save()

            # 4. Prepare and place the order
            try:
                order = CheckoutService.prepare_checkout(
                    cart=cart,
                    user=request.user,
                    shipping_address=shipping_address,
                    payment_method=payment_method,
                    idempotency_key=idempotency_key,
                )

                if payment_method == Order.PAYMENT_METHOD_COD:
                    OrderWorkflowService.confirm_cod_order(order)
                    messages.success(
                        request,
                        f"Order #{order.order_number} confirmed for Cash on Delivery. We will prepare your package shortly!"
                    )
                else:
                    messages.success(
                        request,
                        f"Order #{order.order_number} placed successfully. Please complete simulated online payment to activate fulfillment."
                    )

                return redirect("orders:customer_order_detail", order_number=order.order_number)
            except InsufficientStockError as exc:
                messages.error(request, str(exc))
                return redirect("cart:detail")
            except (InactiveProductError, ValidationError) as exc:
                messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
                return redirect("cart:detail")
    else:
        initial_data = {
            "idempotency_key": uuid.uuid4().hex,
            "payment_method": Order.PAYMENT_METHOD_COD,
        }
        if latest_address:
            initial_data.update({
                "full_name": latest_address.full_name,
                "phone": latest_address.phone,
                "street_address_1": latest_address.street_address_1,
                "street_address_2": latest_address.street_address_2,
                "city": latest_address.city,
                "district": latest_address.district,
                "province": latest_address.province,
                "postal_code": latest_address.postal_code,
            })
        form = CheckoutForm(initial=initial_data, requires_shipping=has_physical, user=request.user)

    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "cart": cart,
            "items": items,
            "analysis": analysis,
            "subtotal": subtotal,
            "has_physical": has_physical,
            "is_cod_eligible": is_cod_eligible,
        },
    )
