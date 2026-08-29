from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Notification

from subscriptions.services.subscription_service import (
    SubscriptionService,
)


class Command(BaseCommand):
    help = "Send subscription expiry reminders"

    def handle(self, *args, **options):

        sent_count = 0

        for days in (7, 3, 1):

            subscriptions = (
                SubscriptionService
                .get_expiring_subscriptions(days)
            )

            for subscription in subscriptions:

                user = subscription.user

                if not user:
                    continue

                # -------------------------------------------------
                # Determine resources covered by subscription
                # -------------------------------------------------

                resource_names = []

                entitlements = (
                    subscription.entitlements
                    .select_related(
                        "track",
                        "exam",
                        "course",
                    )
                    .filter(
                        is_active=True,
                    )
                )

                for entitlement in entitlements:

                    resource = (
                        entitlement.get_resource()
                    )

                    if resource:
                        resource_names.append(
                            str(resource)
                        )

                # -------------------------------------------------
                # Fallback to subscription plan
                # -------------------------------------------------

                if resource_names:

                    resource_name = ", ".join(
                        resource_names
                    )

                elif subscription.plan:

                    resource_name = (
                        subscription.plan.name
                    )

                else:

                    resource_name = "your subscription"

                # -------------------------------------------------
                # Create notification
                # -------------------------------------------------

                notification = (
                    Notification.objects.create(
                        title="Subscription Expiring Soon",
                        message=(
                            f"Your subscription for "
                            f"{resource_name} will expire on "
                            f"{subscription.expires_at.date()}."
                        ),
                    )
                )

                notification.recipients.add(
                    user
                )

                sent_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Subscription expiry reminders sent: "
                f"{sent_count}"
            )
        )