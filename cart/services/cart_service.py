from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

from cart.models import Cart, CartItem
from store.models import Product, ProductVariant


class CartError(Exception):
    pass


class InactiveProductError(CartError):
    pass


class InsufficientStockError(CartError):
    pass


class PriceChangedError(CartError):
    def __init__(self, message, old_price, new_price):
        super().__init__(message)
        self.old_price = old_price
        self.new_price = new_price


class CartService:
    @staticmethod
    def get_or_create_cart(request) -> Cart:
        """
        Safely retrieve or initialize a persistent cart for an authenticated user
        or anonymous session visitor.
        """
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user, defaults={"currency": "NPR"})
            # If session cart exists with items, merge it
            guest_cart_id = request.session.get("guest_cart_id")
            guest_cart = None
            if guest_cart_id:
                guest_cart = Cart.objects.filter(id=guest_cart_id, user__isnull=True).first()
            if not guest_cart and request.session.session_key:
                guest_cart = Cart.objects.filter(session_key=request.session.session_key, user__isnull=True).first()

            if guest_cart and guest_cart.pk != cart.pk:
                CartService.merge_carts(guest_cart, cart)
                if "guest_cart_id" in request.session:
                    del request.session["guest_cart_id"]
            return cart

        # Anonymous guest visitor
        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key, defaults={"currency": "NPR"})
        request.session["guest_cart_id"] = cart.id
        return cart

    @staticmethod
    @transaction.atomic
    def merge_carts(source_cart: Cart, target_cart: Cart):
        """Merge items from anonymous session cart into user's authenticated cart."""
        for item in source_cart.items.select_related("variant"):
            target_item = target_cart.items.filter(variant=item.variant).first()
            if target_item:
                target_item.quantity += item.quantity
                target_item.unit_price_snapshot = item.variant.price
                target_item.save(update_fields=["quantity", "unit_price_snapshot"])
            else:
                item.cart = target_cart
                item.unit_price_snapshot = item.variant.price
                item.save(update_fields=["cart", "unit_price_snapshot"])
        source_cart.delete()

    @staticmethod
    def add_to_cart(cart: Cart, variant_id: int, quantity: int = 1) -> CartItem:
        """
        Add a product variant to cart after verifying it is approved, active,
        and sufficient stock is available.
        """
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")

        variant = (
            ProductVariant.objects
            .select_related("product", "product__vendor")
            .filter(pk=variant_id, is_active=True)
            .first()
        )
        if not variant:
            raise InactiveProductError("The requested product variant is not available.")

        product = variant.product
        if product.approval_status != Product.STATUS_APPROVED or not product.is_active:
            raise InactiveProductError("This product is currently not available for purchase.")

        # Check stock for physical items
        if product.product_type == Product.TYPE_PHYSICAL:
            inv = getattr(variant, "inventory", None)
            if not inv:
                raise InsufficientStockError("Inventory not configured for this product.")
            existing_item = cart.items.filter(variant=variant).first()
            current_cart_qty = existing_item.quantity if existing_item else 0
            total_requested = current_cart_qty + quantity
            if not inv.allow_backorder and total_requested > inv.available_quantity:
                raise InsufficientStockError(
                    f"Only {inv.available_quantity} units available. You already have {current_cart_qty} in cart."
                )

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={
                "quantity": quantity,
                "unit_price_snapshot": variant.price,
            },
        )
        if not created:
            item.quantity += quantity
            item.unit_price_snapshot = variant.price
            item.save(update_fields=["quantity", "unit_price_snapshot"])

        return item

    @staticmethod
    def update_cart_item(cart: Cart, item_id: int, quantity: int) -> CartItem | None:
        """Update quantity of an item in the cart. If quantity <= 0, remove it."""
        item = cart.items.select_related("variant", "variant__product").filter(pk=item_id).first()
        if not item:
            return None

        if quantity <= 0:
            item.delete()
            return None

        # Check stock for physical items
        if item.variant.product.product_type == Product.TYPE_PHYSICAL:
            inv = getattr(item.variant, "inventory", None)
            if inv and not inv.allow_backorder and quantity > inv.available_quantity:
                raise InsufficientStockError(f"Cannot increase quantity to {quantity}. Only {inv.available_quantity} available.")

        item.quantity = quantity
        item.save(update_fields=["quantity"])
        return item

    @staticmethod
    def remove_from_cart(cart: Cart, item_id: int):
        cart.items.filter(pk=item_id).delete()

    @staticmethod
    def validate_cart(cart: Cart) -> dict:
        """
        Validate cart state prior to checkout:
        - Removes inactive or unapproved products.
        - Updates price snapshots and flags any price changes.
        - Computes composition flags (has_physical, has_digital, is_mixed, is_cod_eligible).
        """
        items = list(cart.items.select_related("variant", "variant__product", "variant__product__vendor"))
        if not items:
            raise ValidationError("Your cart is empty.")

        removed_items = []
        price_changes = []
        has_physical = False
        has_digital = False
        all_cod_eligible = True

        for item in items:
            prod = item.variant.product
            # 1. Product active check
            if prod.approval_status != Product.STATUS_APPROVED or not prod.is_active or not item.variant.is_active:
                removed_items.append(item.variant.product.title)
                item.delete()
                continue

            # 2. Price change check
            if item.unit_price_snapshot != item.variant.price:
                old_p = item.unit_price_snapshot
                item.unit_price_snapshot = item.variant.price
                item.save(update_fields=["unit_price_snapshot"])
                price_changes.append({
                    "item": prod.title,
                    "old_price": old_p,
                    "new_price": item.variant.price,
                })

            # 3. Product type analysis
            if prod.product_type == Product.TYPE_PHYSICAL:
                has_physical = True
                vendor = prod.vendor
                vendor_cod = vendor.is_cod_enabled if vendor else True
                if not (prod.is_cod_eligible and vendor_cod):
                    all_cod_eligible = False
            elif prod.product_type == Product.TYPE_DIGITAL:
                has_digital = True

        # Refresh remaining items
        remaining_items = cart.items.all()
        if not remaining_items.exists():
            raise InactiveProductError("All items in your cart became unavailable and were removed.")

        is_mixed = has_physical and has_digital
        # COD is ONLY allowed if there are physical items, NO digital items, and all physical products/vendors are COD-enabled
        is_cod_eligible = has_physical and (not has_digital) and all_cod_eligible

        return {
            "valid": True,
            "has_physical": has_physical,
            "has_digital": has_digital,
            "is_mixed": is_mixed,
            "is_cod_eligible": is_cod_eligible,
            "removed_items": removed_items,
            "price_changes": price_changes,
            "subtotal": sum(it.total_price for it in remaining_items),
        }
