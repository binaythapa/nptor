from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import Http404

from courses.models import Course
from subscriptions.services.access_service import AccessService
from subscriptions.services.plan_service import get_plan_for_course


def course_learning_access_required(view_func):
    """
    Enforce access to course learning content before the student
    learning view runs.

    Public visibility is not the same as paid access. A public course
    may be listed in the catalog while its lessons remain locked until
    the user owns an active entitlement.

    Exceptions:
        - Course owner may use the existing preview mode.
        - Platform staff/superusers may use the existing preview mode.
        - Courses with no active plan are treated as legacy/free courses.
        - A zero-price active plan is treated as free.
    """

    @wraps(view_func)
    def _wrapped(request, slug, *args, **kwargs):
        course = Course.objects.get(slug=slug)

        is_owner = course.created_by_id == request.user.id
        is_admin = request.user.is_staff or request.user.is_superuser
        preview_requested = request.GET.get("preview") == "1"

        if preview_requested and (is_owner or is_admin):
            return view_func(request, slug, *args, **kwargs)

        if not (
            course.approval_status == Course.APPROVAL_APPROVED
            and course.is_published
            and course.is_public
        ):
            raise Http404("Course not found.")

        plan = get_plan_for_course(course, None)

        if plan is None or plan.price == 0:
            return view_func(request, slug, *args, **kwargs)

        if not AccessService.has_access(
            student=request.user,
            resource_type=AccessService.RESOURCE_COURSE,
            resource=course,
        ):
            raise PermissionDenied(
                "You do not have access to this course."
            )

        return view_func(request, slug, *args, **kwargs)

    return _wrapped
