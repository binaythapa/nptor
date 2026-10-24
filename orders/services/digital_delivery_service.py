from datetime import timedelta
import secrets
from typing import Optional, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from orders.models import DigitalDelivery, Order, OrderItem
from store.models import ProductDigitalAsset


class DigitalDeliveryService:
    DEFAULT_VALIDITY_DAYS = 30
    DEFAULT_MAX_DOWNLOADS = 5

    @classmethod
    def generate_delivery_token(
        cls,
        *,
        order_item: OrderItem,
        user,
        digital_asset: ProductDigitalAsset,
        validity_days: int = DEFAULT_VALIDITY_DAYS,
        max_downloads: int = DEFAULT_MAX_DOWNLOADS,
    ) -> DigitalDelivery:
        """
        Creates a secure, cryptographically random download token (64-character hex).
        """
        token = secrets.token_hex(32)
        expires_at = timezone.now() + timedelta(days=validity_days)

        delivery, created = DigitalDelivery.objects.get_or_create(
            order_item=order_item,
            defaults={
                "user": user,
                "digital_asset": digital_asset,
                "download_token": token,
                "expires_at": expires_at,
                "max_downloads": max_downloads,
                "download_count": 0,
                "is_revoked": False,
            },
        )
        return delivery

    @classmethod
    def claim_and_reserve_download(
        cls,
        download_token: str,
        user,
    ) -> Tuple[bool, str, int, Optional[DigitalDelivery]]:
        """
        Atomically validates the download request and reserves/increments the download count
        under a row-level database lock (select_for_update).
        Guarantees that concurrent requests cannot exceed max_downloads (eliminating TOCTOU race conditions).
        Returns: (is_valid, reason_message, http_status_code, delivery_instance)
        """
        if not download_token or len(download_token) != 64:
            return False, "Invalid or malformed download token.", 404, None

        with transaction.atomic():
            delivery = (
                DigitalDelivery.objects
                .select_for_update()
                .select_related(
                    "user",
                    "digital_asset",
                    "order_item",
                    "order_item__suborder",
                    "order_item__suborder__master_order",
                )
                .filter(download_token=download_token)
                .first()
            )

            if not delivery:
                return False, "Download token not found.", 404, None

            # 1. Authorization: user must own this delivery
            if delivery.user_id != user.id and not user.is_staff:
                return False, "You are not authorized to download this file.", 403, delivery

            # 2. Payment verification: master order must be PAID
            master_order = delivery.order_item.suborder.master_order
            if master_order.online_payment_status != Order.ONLINE_STATUS_PAID:
                return False, "Download unavailable: order payment has not been verified.", 403, delivery

            # 3. Revocation check (e.g. order refunded or cancelled)
            if delivery.is_revoked:
                return False, "This download license has been revoked or refunded.", 410, delivery

            # 4. Expiry check
            if timezone.now() > delivery.expires_at:
                return False, "This download link has expired.", 410, delivery

            # 5. Download count limit
            if delivery.download_count >= delivery.max_downloads:
                return False, f"Maximum download limit ({delivery.max_downloads}) reached for this file.", 403, delivery

            # 6. Physical asset verification
            if not delivery.digital_asset or not delivery.digital_asset.file:
                return False, "Digital asset file is missing or unattached.", 404, delivery

            # Verify the file is physically present and readable
            try:
                test_file = delivery.digital_asset.file.open("rb")
                test_file.close()
            except (FileNotFoundError, ValueError, OSError):
                return False, "Digital asset file is missing or unattached.", 404, delivery

            # Atomically reserve the download slot while holding the row lock
            delivery.download_count += 1
            delivery.save(update_fields=["download_count"])

            return True, "Valid", 200, delivery

    @classmethod
    def validate_download_request(
        cls,
        download_token: str,
        user,
    ) -> Tuple[bool, str, int, Optional[DigitalDelivery]]:
        """
        Validates the download request against strict business and security rules.
        Returns: (is_valid, reason_message, http_status_code, delivery_instance)
        """
        if not download_token or len(download_token) != 64:
            return False, "Invalid or malformed download token.", 404, None

        delivery = (
            DigitalDelivery.objects
            .select_related(
                "user",
                "digital_asset",
                "order_item",
                "order_item__suborder",
                "order_item__suborder__master_order",
            )
            .filter(download_token=download_token)
            .first()
        )

        if not delivery:
            return False, "Download token not found.", 404, None

        # 1. Authorization: user must own this delivery
        if delivery.user_id != user.id and not user.is_staff:
            return False, "You are not authorized to download this file.", 403, delivery

        # 2. Payment verification: master order must be PAID
        master_order = delivery.order_item.suborder.master_order
        if master_order.online_payment_status != Order.ONLINE_STATUS_PAID:
            return False, "Download unavailable: order payment has not been verified.", 403, delivery

        # 3. Revocation check (e.g. order refunded or cancelled)
        if delivery.is_revoked:
            return False, "This download license has been revoked or refunded.", 410, delivery

        # 4. Expiry check
        if timezone.now() > delivery.expires_at:
            return False, "This download link has expired.", 410, delivery

        # 5. Download count limit
        if delivery.download_count >= delivery.max_downloads:
            return False, f"Maximum download limit ({delivery.max_downloads}) reached for this file.", 403, delivery

        # 6. Physical asset verification
        if not delivery.digital_asset or not delivery.digital_asset.file:
            return False, "Digital asset file is missing or unattached.", 404, delivery

        return True, "Valid", 200, delivery

    @classmethod
    def record_download(cls, delivery: DigitalDelivery) -> int:
        """
        Atomically increments download_count using database row locking.
        Returns the updated download count.
        """
        with transaction.atomic():
            deliv = DigitalDelivery.objects.select_for_update().get(id=delivery.id)
            deliv.download_count += 1
            deliv.save(update_fields=["download_count"])
            return deliv.download_count

    @classmethod
    def revoke_delivery(cls, order_item: OrderItem, reason: str = "") -> bool:
        """
        Revokes a digital delivery token upon refund or cancellation.
        """
        delivery = DigitalDelivery.objects.filter(order_item=order_item).first()
        if delivery:
            delivery.is_revoked = True
            delivery.save(update_fields=["is_revoked"])
            return True
        return False
