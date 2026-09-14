from django.utils import timezone

from .subscription_service import SubscriptionService
from .access_service import AccessService as _ResourceAccessService
from .account_access_service import AccountAccessService
from .global_access import has_all_access_subscription
from organizations.models import ResourceAccess


class AccessService(_ResourceAccessService):
    """Unified subscriber/resource access policy."""

    @staticmethod
    def has_platform_access(student):
        return has_all_access_subscription(student)

    @staticmethod
    def _has_organization_assignment_access(student, resource_type, resource):
        """Return assigned organization access without evaluating payment."""
        organization = getattr(resource, "organization", None)
        if organization is None:
            return None

        resource_field = {
            _ResourceAccessService.RESOURCE_COURSE: "course",
            _ResourceAccessService.RESOURCE_TRACK: "track",
            _ResourceAccessService.RESOURCE_EXAM: "exam",
        }.get(resource_type)
        if not resource_field:
            return False

        now = timezone.now()
        today = timezone.localdate(now)
        accesses = (
            ResourceAccess.objects
            .select_related("assignment", "organization")
            .filter(
                user=student,
                resource_type=resource_type,
                source=ResourceAccess.SOURCE_ORGANIZATION,
                organization=organization,
                is_active=True,
                assignment__student=student,
                assignment__organization=organization,
                assignment__is_active=True,
                **{resource_field: resource},
            )
            .order_by("-granted_at")
        )

        for access in accesses:
            if access.revoked_at or not access.organization.is_active:
                continue

            assignment = access.assignment
            starts_at = getattr(assignment, "starts_at", None)
            expires_at = getattr(assignment, "expires_at", None)
            start_date = timezone.localtime(starts_at).date() if starts_at else None
            expires_date = timezone.localtime(expires_at).date() if expires_at else None

            # Organization assignment dates are calendar dates. This keeps
            # access aligned with the dates shown to the student and avoids
            # locking an assignment because the server is still on the prior
            # UTC calendar day.
            if start_date and today < start_date:
                continue
            if expires_date and today > expires_date:
                continue

            return True

        return False

    @staticmethod
    def has_course_access(student, course):
        if not student or not course:
            return False

        organization_access = AccessService._has_organization_assignment_access(
            student,
            _ResourceAccessService.RESOURCE_COURSE,
            course,
        )
        if organization_access is not None:
            return organization_access

        if has_all_access_subscription(student) or AccountAccessService.has_course_access(student, course):
            return True
        if getattr(course, "is_publicly_available", lambda: False)():
            plans = list(course.subscription_plans.filter(is_active=True))
            if not plans or any(plan.price <= 0 for plan in plans):
                return True
        return _ResourceAccessService.has_access(
            student=student,
            resource_type=_ResourceAccessService.RESOURCE_COURSE,
            resource=course,
        )

    @staticmethod
    def has_track_access(student, track):
        if not student or not track:
            return False

        organization_access = AccessService._has_organization_assignment_access(
            student,
            _ResourceAccessService.RESOURCE_TRACK,
            track,
        )
        if organization_access is not None:
            return organization_access

        if has_all_access_subscription(student) or AccountAccessService.has_track_access(student, track):
            return True
        if getattr(track, "organization_id", None) is None and track.is_free():
            return True
        return _ResourceAccessService.has_access(
            student=student,
            resource_type=_ResourceAccessService.RESOURCE_TRACK,
            resource=track,
        )

    @staticmethod
    def has_exam_access(student, exam):
        if not student or not exam:
            return False

        organization_access = AccessService._has_organization_assignment_access(
            student,
            _ResourceAccessService.RESOURCE_EXAM,
            exam,
        )
        if organization_access is not None:
            return organization_access

        if has_all_access_subscription(student):
            return True

        # Direct admin/system access remains a compatibility path. Purchased
        # exam access is no longer a product; normal subscriber access is
        # inherited only through Course or Track parents.
        if _ResourceAccessService.has_access(
            student=student,
            resource_type=_ResourceAccessService.RESOURCE_EXAM,
            resource=exam,
        ):
            return True

        from courses.models import CourseExam
        from quiz.models import TrackExam

        for membership in CourseExam.objects.filter(exam=exam).select_related("course"):
            if AccessService.has_course_access(student, membership.course):
                return True
        for membership in TrackExam.objects.filter(exam=exam).select_related("track"):
            if AccessService.has_track_access(student, membership.track):
                return True
        return False

    @staticmethod
    def has_access(*, student, resource_type, resource):
        if resource_type == _ResourceAccessService.RESOURCE_COURSE:
            return AccessService.has_course_access(student, resource)
        if resource_type == _ResourceAccessService.RESOURCE_TRACK:
            return AccessService.has_track_access(student, resource)
        if resource_type == _ResourceAccessService.RESOURCE_EXAM:
            return AccessService.has_exam_access(student, resource)
        return False
