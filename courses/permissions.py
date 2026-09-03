from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import Http404

from courses.models import Course, Lesson
from subscriptions.services.access_service import AccessService
from subscriptions.services.plan_service import get_plan_for_course


def _course_requires_paid_access(course):
    plan = get_plan_for_course(course, None)
    return plan is not None and plan.price > 0


def _user_has_course_access(user, course):
    if not _course_requires_paid_access(course):
        return True

    return AccessService.has_access(
        student=user,
        resource_type=AccessService.RESOURCE_COURSE,
        resource=course,
    )


def course_learning_access_required(view_func):
    """Enforce access to course learning content."""

    @wraps(view_func)
    def _wrapped(request, slug, *args, **kwargs):
        course = Course.objects.filter(slug=slug).first()
        if course is None:
            raise Http404("Course not found.")

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

        if not _user_has_course_access(request.user, course):
            raise PermissionDenied("You do not have access to this course.")

        return view_func(request, slug, *args, **kwargs)

    return _wrapped


def lesson_course_access_required(view_func):
    """Require access to the course containing a lesson."""

    @wraps(view_func)
    def _wrapped(request, slug, lesson_id, *args, **kwargs):
        lesson = Lesson.objects.select_related("section__course").filter(
            id=lesson_id
        ).first()

        if lesson is None or lesson.section.course.slug != slug:
            raise Http404("Lesson not found.")

        course = lesson.section.course
        is_owner = course.created_by_id == request.user.id
        is_admin = request.user.is_staff or request.user.is_superuser
        preview_requested = request.GET.get("preview") == "1"

        if preview_requested and (is_owner or is_admin):
            return view_func(request, slug, lesson_id, *args, **kwargs)

        if not (
            course.approval_status == Course.APPROVAL_APPROVED
            and course.is_published
            and course.is_public
        ):
            raise Http404("Course not found.")

        if not _user_has_course_access(request.user, course):
            raise PermissionDenied("You do not have access to this course.")

        return view_func(request, slug, lesson_id, *args, **kwargs)

    return _wrapped


def video_progress_access_required(view_func):
    """Require course access before recording video progress."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        lesson_id = request.POST.get("lesson_id")

        try:
            lesson_id = int(lesson_id)
        except (TypeError, ValueError):
            return view_func(request, *args, **kwargs)

        lesson = Lesson.objects.select_related("section__course").filter(
            id=lesson_id
        ).first()

        if lesson is None:
            return view_func(request, *args, **kwargs)

        course = lesson.section.course

        if not (
            course.approval_status == Course.APPROVAL_APPROVED
            and course.is_published
            and course.is_public
        ):
            return view_func(request, *args, **kwargs)

        if not _user_has_course_access(request.user, course):
            raise PermissionDenied("You do not have access to this course.")

        return view_func(request, *args, **kwargs)

    return _wrapped
