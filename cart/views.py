from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from cart.services.cart_service import (
    CartService,
    InactiveProductError,
    InsufficientStockError,
    PriceChangedError,
)
from store.models import ProductVariant


def cart_detail(request):
    """
    Renders customer shopping cart with line items, prices, and stock validations.
    Works for both authenticated users and anonymous session visitors.
    """
    cart = CartService.get_or_create_cart(request)
    items = cart.items.select_related("variant", "variant__product", "variant__product__vendor").order_by("added_at")

    analysis = None
    price_warnings = []
    removed_warnings = []

    if items.exists():
        try:
            analysis = CartService.validate_cart(cart)
            if analysis.get("price_changes"):
                for change in analysis["price_changes"]:
                    price_warnings.append(
                        f"Price for '{change['item']}' changed from NPR {change['old_price']} to NPR {change['new_price']}."
                    )
            if analysis.get("removed_items"):
                for item_name in analysis["removed_items"]:
                    removed_warnings.append(
                        f"'{item_name}' is no longer available and was removed from your cart."
                    )
        except InactiveProductError as exc:
            messages.warning(request, str(exc))
        except ValidationError:
            pass

    for warn in price_warnings:
        messages.warning(request, warn)
    for warn in removed_warnings:
        messages.info(request, warn)

    # Re-fetch items after validation
    items = cart.items.select_related("variant", "variant__product", "variant__product__vendor").order_by("added_at")
    subtotal = sum(item.total_price for item in items)

    return render(
        request,
        "cart/cart_detail.html",
        {
            "cart": cart,
            "items": items,
            "subtotal": subtotal,
            "analysis": analysis,
        },
    )


@require_POST
def cart_add(request, variant_id):
    """
    Adds a product variant to the customer's cart.
    Validates stock availability and active status before adding.
    """
    cart = CartService.get_or_create_cart(request)
    raw_qty = request.POST.get("quantity", 1)
    try:
        quantity = int(raw_qty)
        if quantity < 1:
            quantity = 1
    except (ValueError, TypeError):
        quantity = 1

    next_url = request.POST.get("next") or reverse("cart:detail")

    variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=variant_id)
    if variant.product.is_digital and not (request.user.is_authenticated and request.user.is_staff):
        messages.warning(
            request,
            f"'{variant.product.title}' is a digital product and is currently in preview mode. Digital purchases will be enabled in a future release."
        )
        return redirect(next_url)

    try:
        item = CartService.add_to_cart(cart, variant_id=variant_id, quantity=quantity)
        messages.success(request, f"Added {item.variant.product.title} ({quantity}x) to your cart.")
    except InsufficientStockError as exc:
        messages.error(request, str(exc))
    except InactiveProductError as exc:
        messages.error(request, str(exc))
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))

    return redirect(next_url)


@require_POST
def cart_update(request, item_id):
    """
    Updates the quantity of a specific cart item.
    If quantity <= 0, the item is removed.
    """
    cart = CartService.get_or_create_cart(request)
    raw_qty = request.POST.get("quantity", 1)
    try:
        quantity = int(raw_qty)
    except (ValueError, TypeError):
        quantity = 1

    try:
        updated_item = CartService.update_cart_item(cart, item_id=item_id, quantity=quantity)
        if updated_item:
            messages.success(request, f"Updated quantity to {quantity}.")
        else:
            messages.info(request, "Item removed from cart.")
    except InsufficientStockError as exc:
        messages.error(request, str(exc))
    except ValidationError as exc:
        messages.error(request, str(exc))

    return redirect(reverse("cart:detail"))


@require_POST
def cart_remove(request, item_id):
    """
    Removes an item completely from the cart.
    """
    cart = CartService.get_or_create_cart(request)
    CartService.remove_from_cart(cart, item_id=item_id)
    messages.info(request, "Item removed from cart.")
    return redirect(reverse("cart:detail"))


@require_POST
def cart_clear(request):
    """
    Empties the current cart.
    """
    cart = CartService.get_or_create_cart(request)
    cart.items.all().delete()
    messages.info(request, "Your cart has been cleared.")
    return redirect(reverse("cart:detail"))
