from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


def delete_expired_unverified_users(minutes=30):
    cutoff = timezone.now() - timedelta(minutes=minutes)

    User.objects.filter(
        is_active=False,
        date_joined__lt=cutoff,
    ).delete()
