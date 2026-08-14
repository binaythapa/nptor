# accounts/services/cleanup.py

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone


User = get_user_model()


def delete_expired_unverified_users(minutes=30):
    """
    Delete inactive users who have not verified their email
    within the specified registration period.

    Returns:
        Number of deleted users.
    """

    cutoff = (
        timezone.now()
        - timedelta(minutes=minutes)
    )

    deleted_count, _ = (
        User.objects
        .filter(
            is_active=False,
            profile__email_verified=False,
            date_joined__lt=cutoff,
        )
        .delete()
    )

    return deleted_count