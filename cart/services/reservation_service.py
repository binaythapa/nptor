from datetime import timedelta
from django.db import transaction
from django.utils import timezone

from cart.models import Cart, StockReservation
from cart.services.cart_service import InsufficientStockError
from store.models import Product, ProductInventory


class ReservationService:
    DEFAULT_TTL_MINUTES = 15

    @classmethod
    def reserve_cart_stock(cls, cart: Cart, ttl_minutes: int = DEFAULT_TTL_MINUTES) -> list[StockReservation]:
        """
        Atomically reserve inventory for all physical items in the cart.
        Uses row-level locking (select_for_update) to guarantee no overselling.
        """
        # First release any expired reservations platform-wide
        cls.release_expired_reservations()

        reservations = []
        expires_at = timezone.now() + timedelta(minutes=ttl_minutes)

        with transaction.atomic():
            # Release any existing active reservations for this cart first to avoid duplicate holds
            cls.release_cart_reservations(cart)

            # Sort variants by ID to ensure deterministic lock ordering and prevent deadlocks
            items = list(cart.items.select_related("variant", "variant__product").order_by("variant_id"))

            for item in items:
                variant = item.variant
                product = variant.product

                if product.product_type != Product.TYPE_PHYSICAL:
                    continue  # Digital products do not hold physical inventory

                # Acquire row lock on inventory
                inventory = (
                    ProductInventory.objects
                    .select_for_update()
                    .get(variant_id=variant.id)
                )

                available = inventory.quantity - inventory.reserved_quantity
                if not inventory.allow_backorder and available < item.quantity:
                    raise InsufficientStockError(
                        f"Stock unavailable for '{product.title}'. Requested: {item.quantity}, Available: {max(0, available)}."
                    )

                inventory.reserved_quantity += item.quantity
                inventory.save(update_fields=["reserved_quantity", "updated_at"])

                res, created = StockReservation.objects.update_or_create(
                    cart=cart,
                    variant=variant,
                    defaults={
                        "reserved_units": item.quantity,
                        "expires_at": expires_at,
                        "is_released": False,
                    },
                )
                reservations.append(res)

        return reservations

    @classmethod
    def release_cart_reservations(cls, cart: Cart):
        """Release all active reservations for a specific cart (e.g. checkout cancelled or refreshed)."""
        active_holds = cart.stock_reservations.filter(is_released=False).select_related("variant")
        if not active_holds.exists():
            return

        with transaction.atomic():
            for hold in active_holds:
                inv = ProductInventory.objects.select_for_update().filter(variant_id=hold.variant_id).first()
                if inv:
                    inv.reserved_quantity = max(0, inv.reserved_quantity - hold.reserved_units)
                    inv.save(update_fields=["reserved_quantity", "updated_at"])
                hold.is_released = True
                hold.save(update_fields=["is_released"])

    @classmethod
    def release_expired_reservations(cls) -> int:
        """
        Find and release all expired reservations across all carts.
        Returns the number of reservations released.
        """
        now = timezone.now()
        expired_holds = (
            StockReservation.objects
            .filter(is_released=False, expires_at__lt=now)
            .select_related("variant")
        )

        released_count = 0
        with transaction.atomic():
            for hold in expired_holds:
                inv = ProductInventory.objects.select_for_update().filter(variant_id=hold.variant_id).first()
                if inv:
                    inv.reserved_quantity = max(0, inv.reserved_quantity - hold.reserved_units)
                    inv.save(update_fields=["reserved_quantity", "updated_at"])
                hold.is_released = True
                hold.save(update_fields=["is_released"])
                released_count += 1

        return released_count

    @classmethod
    def consume_reservations_for_order(cls, order) -> None:
        """
        Permanently deducts inventory for physical items in an order and marks
        temporary reservations as consumed/released so reserved units are not double-counted.
        Uses deterministic row-level locking on ProductInventory.
        """
        with transaction.atomic():
            variant_quantities = {}
            for suborder in order.suborders.all():
                for item in suborder.items.select_related("variant", "variant__product"):
                    if item.variant and item.variant.product.product_type == Product.TYPE_PHYSICAL:
                        variant_quantities[item.variant_id] = variant_quantities.get(item.variant_id, 0) + item.quantity

            for variant_id in sorted(variant_quantities.keys()):
                qty = variant_quantities[variant_id]
                inv = ProductInventory.objects.select_for_update().filter(variant_id=variant_id).first()
                if inv:
                    inv.quantity = max(0, inv.quantity - qty)
                    inv.reserved_quantity = max(0, inv.reserved_quantity - qty)
                    inv.save(update_fields=["quantity", "reserved_quantity", "updated_at"])

            # Release any remaining active reservations for this user's cart
            user_cart = Cart.objects.filter(user=order.user).first()
            if user_cart:
                user_cart.stock_reservations.filter(is_released=False).update(is_released=True)

    @classmethod
    def restore_inventory_for_items(cls, items_list) -> None:
        """
        Restores physical quantity back to ProductInventory when an order or suborder
        is cancelled or returned post-confirmation.
        """
        with transaction.atomic():
            variant_quantities = {}
            for item in items_list:
                if item.variant and item.variant.product.product_type == Product.TYPE_PHYSICAL:
                    variant_quantities[item.variant_id] = variant_quantities.get(item.variant_id, 0) + item.quantity

            for variant_id in sorted(variant_quantities.keys()):
                qty = variant_quantities[variant_id]
                inv = ProductInventory.objects.select_for_update().filter(variant_id=variant_id).first()
                if inv:
                    inv.quantity += qty
                    inv.save(update_fields=["quantity", "updated_at"])

