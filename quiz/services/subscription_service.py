from quiz.models import ExamSubscription, ExamTrackSubscription


class SubscriptionService:
    """
    Single source of truth for subscriptions
    """

    @staticmethod
    def subscribe(
        *,
        user,
        exam=None,
        track=None,
        amount=0,
        payment_required=False,
        expires_at=None,
        subscribed_by_admin=False,
    ):
        if exam:
            ExamSubscription.objects.update_or_create(
                user=user,
                exam=exam,
                defaults={
                    "is_active": True,
                    "payment_required": payment_required,
                    "amount": amount,
                    "currency": "INR",
                    "expires_at": expires_at,
                    "subscribed_by_admin": subscribed_by_admin,
                },
            )

        if track:
            ExamTrackSubscription.objects.update_or_create(
                user=user,
                track=track,
                defaults={
                    "is_active": True,
                    "payment_required": payment_required,
                    "amount": amount,
                    "currency": "INR",
                    "expires_at": expires_at,
                    "subscribed_by_admin": subscribed_by_admin,
                },
            )
