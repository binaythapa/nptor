from django.db.models import Q

from quiz.models import Exam, ExamTrack, LearningShortlist
from subscriptions.services import AccessService


def _active_plans(resource):
    prefetched = getattr(resource, "_prefetched_objects_cache", {}).get("subscription_plans")
    if prefetched is not None:
        return [plan for plan in prefetched if getattr(plan, "is_active", True)]

    manager = getattr(resource, "subscription_plans", None)
    if manager is None:
        return []
    if hasattr(manager, "filter"):
        return list(manager.filter(is_active=True))
    return [plan for plan in manager if getattr(plan, "is_active", True)]


def _has_access(user, resource_type, resource):
    return AccessService.has_access(student=user, resource_type=resource_type, resource=resource)
