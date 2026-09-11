from .subscription_service import SubscriptionService
from .access_service import AccessService as _ResourceAccessService
from .global_access import has_all_access_subscription
from subscriptions.models import Subscription, SubscriptionEntitlement


class AccessService(_ResourceAccessService):
    """Resource access service with platform-wide and track-included access."""

    @staticmethod
    def has_platform_access(student):
        return has_all_access_subscription(student)

    @staticmethod
    def has_access(*, student, resource_type, resource):
        if has_all_access_subscription(student):
            return True

        if resource_type == _ResourceAccessService.RESOURCE_COURSE:
            if SubscriptionEntitlement.objects.filter(
                subscription__user=student,
                subscription__status=Subscription.STATUS_ACTIVE,
                resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
                track__courses=resource,
                is_active=True,
            ).exists():
                return True

        return _ResourceAccessService.has_access(
            student=student,
            resource_type=resource_type,
            resource=resource,
        )
