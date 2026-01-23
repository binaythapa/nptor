from django.core.management.base import BaseCommand
from django.utils import timezone

from quiz.services.subscription_service import SubscriptionService
from quiz.services.notification_service import NotificationService


class Command(BaseCommand):
    help = "Send subscription expiry reminders"

    def handle(self, *args, **options):
        for days in (7, 3, 1):

            track_subs, exam_subs = SubscriptionService.get_expiring_subscriptions(days)

            for sub in track_subs:
                NotificationService.notify_expiry(
                    user=sub.user,
                    title="Subscription expiring soon",
                    message=(
                        f"Your subscription for '{sub.track.title}' "
                        f"expires on {sub.expires_at.date()}."
                    )
                )

            for sub in exam_subs:
                NotificationService.notify_expiry(
                    user=sub.user,
                    title="Exam access expiring soon",
                    message=(
                        f"Your access to exam '{sub.exam.title}' "
                        f"expires on {sub.expires_at.date()}."
                    )
                )

        self.stdout.write(self.style.SUCCESS("Expiry reminders sent"))
