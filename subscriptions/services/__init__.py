from .subscription_service import SubscriptionService
from .access_service import AccessService as _ResourceAccessService
from .account_access_service import AccountAccessService
from .global_access import has_all_access_subscription
from subscriptions.models import Subscription, SubscriptionEntitlement


class AccessService(_ResourceAccessService):
    """Unified subscriber/resource access policy."""

    @staticmethod
    def has_platform_access(student):
        return has_all_access_subscription(student)

    @staticmethod
    def has_course_access(student, course):
        if has_all_access_subscription(student):
            return True
        if AccountAccessService.has_course_access(student, course):
            return True
        return _ResourceAccessService.has_access(
            student=student,
            resource_type=_ResourceAccessService.RESOURCE_COURSE,
            resource=course,
        )

    @staticmethod
    def has_track_access(student, track):
        if has_all_access_subscription(student):
            return True
        if AccountAccessService.has_track_access(student, track):
            return True
        return _ResourceAccessService.has_access(
            student=student,
            resource_type=_ResourceAccessService.RESOURCE_TRACK,
            resource=track,
        )

    @staticmethod
    def has_exam_access(student, exam):
        if has_all_access_subscription(student):
            return True

        # A direct admin/system ResourceAccess record remains a legitimate
        # compatibility path, but subscription product ownership is inherited
        # only through Course or Track parents.
        direct = ResourceAccess = _ResourceAccessService
        if _ResourceAccessService.has_access(
            student=student,
            resource_type=_ResourceAccessService.RESOURCE_EXAM,
            resource=exam,
        ):
            return True

        from courses.models import CourseExam
        from quiz.models import TrackExam

        if CourseExam.objects.filter(exam=exam).exists():
            if any(
                AccessService.has_course_access(student, course)
                for course in CourseExam.objects.filter(exam=exam).values_list("course", flat=True)
            ):
                return True

        for track_id in TrackExam.objects.filter(exam=exam).values_list("track", flat=True):
            from quiz.models import ExamTrack
            track = ExamTrack.objects.filter(pk=track_id).first()
            if track and AccessService.has_track_access(student, track):
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
