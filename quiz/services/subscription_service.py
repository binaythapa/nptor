from django.db import transaction
from django.utils import timezone

from quiz.models import (
    ExamTrack,
    ExamTrackSubscription,
    SubscriptionPlan,
)
from quiz.services.payment_service import PaymentService


class SubscriptionService:
    """
    Handles subscription lifecycle:
    renew / upgrade / downgrade
    """

    # -------------------------------------------------
    # RENEW (same plan)
    # -------------------------------------------------
    @staticmethod
    @transaction.atomic
    def renew_track(*, user, track: ExamTrack, plan: SubscriptionPlan):
        sub = ExamTrackSubscription.objects.get(
            user=user,
            track=track,
            is_active=True,
        )

        base_date = sub.expires_at or timezone.now()

        sub.expires_at = base_date + timezone.timedelta(
            days=plan.duration_days
        )
        sub.amount += plan.price
        sub.save(update_fields=["expires_at", "amount"])

        return sub

    # -------------------------------------------------
    # UPGRADE (immediate)
    # -------------------------------------------------
    @staticmethod
    @transaction.atomic
    def upgrade_track(*, user, track: ExamTrack, new_plan: SubscriptionPlan):
        # Disable old subscription
        ExamTrackSubscription.objects.filter(
            user=user,
            track=track,
            is_active=True,
        ).update(is_active=False)

        # Create new one via payment service
        PaymentService.apply_payment(
            user=user,
            track=track,
            plan=new_plan,
            source="upgrade",
        )

    # -------------------------------------------------
    # DOWNGRADE (after expiry)
    # -------------------------------------------------
    @staticmethod
    def downgrade_track(*, user, track: ExamTrack, new_plan: SubscriptionPlan):
        sub = ExamTrackSubscription.objects.get(
            user=user,
            track=track,
            is_active=True,
        )

        # Minimal implementation (future-proof)
        sub.next_plan = new_plan  # optional future field
        sub.save(update_fields=["next_plan"])
