from subscriptions.services.account_access_service import AccountAccessService


def has_all_access_subscription(user):
    """Return True when the user has a valid Account all-access subscription."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return any(
        subscription.plan.is_all_access()
        and subscription.is_valid()
        for subscription in AccountAccessService._valid_account_subscriptions(user)
    )
