from django.utils import timezone

from subscriptions.models import Subscription, SubscriptionPlan


def has_all_access_subscription(user):
    """Return True when the user has a valid platform-wide subscription."""
    if not user or not getattr(user, "is_authenticated", False):
        return False

    now = timezone.now()
    return Subscription.objects.filter(
        user=user,
        plan__scope=SubscriptionPlan.SCOPE_ALL_ACCESS,
        plan__is_active=True,
        status=Subscription.STATUS_ACTIVE,
        starts_at__lte=now,
    ).filter(
        # NULL expiry means lifetime; otherwise it must still be in the future.
        expires_at__isnull=True,
    ).exists() or Subscription.objects.filter(
        user=user,
        plan__scope=SubscriptionPlan.SCOPE_ALL_ACCESS,
        plan__is_active=True,
        status=Subscription.STATUS_ACTIVE,
        starts_at__lte=now,
        expires_at__gt=now,
    ).exists()
