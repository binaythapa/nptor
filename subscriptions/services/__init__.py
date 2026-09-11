from .subscription_service import SubscriptionService
from .access_service import AccessService as _ResourceAccessService
from .global_access import has_all_access_subscription


class AccessService(_ResourceAccessService):
    """Resource access service with platform-wide subscription precedence."""

    @staticmethod
    def has_access(*, student, resource_type, resource):
        if has_all_access_subscription(student):
            return True
        return _ResourceAccessService.has_access(
            student=student,
            resource_type=resource_type,
            resource=resource,
        )
