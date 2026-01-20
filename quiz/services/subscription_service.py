from django.utils import timezone
from quiz.models import ExamSubscription, ExamTrackSubscription

class SubscriptionService:

    @staticmethod
    def create_exam_subscription(
        user, exam, *, expires_at=None,
        payment_required=False, subscribed_by_admin=False
    ):
        return ExamSubscription.objects.update_or_create(
            user=user,
            exam=exam,
            defaults={
                "is_active": True,
                "expires_at": expires_at,
                "payment_required": payment_required,
                "subscribed_by_admin": subscribed_by_admin,
            }
        )

    @staticmethod
    def create_track_subscription(
        user, track, *, expires_at=None,
        payment_required=False, subscribed_by_admin=False
    ):
        return ExamTrackSubscription.objects.update_or_create(
            user=user,
            track=track,
            defaults={
                "is_active": True,
                "expires_at": expires_at,
                "payment_required": payment_required,
                "subscribed_by_admin": subscribed_by_admin,
            }
        )
