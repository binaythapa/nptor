from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.models import Notification

from courses.models import Course

from courses.services.permissions import (
    can_submit_course_for_review,
    can_approve_course,
    can_request_changes,
    can_reject_course,
    can_publish_course,
    can_edit_course,
)


User = get_user_model()


def _notify_admins(*, title, message):
    admins = User.objects.filter(is_superuser=True, is_active=True)
    notification = Notification.objects.create(title=title, message=message)
    if admins.exists():
        notification.recipients.add(*admins)
    return notification


def _notify_course_owner(*, course, title, message):
    if not course.created_by:
        return None
    notification = Notification.objects.create(title=title, message=message)
    notification.recipients.add(course.created_by)
    return notification


@transaction.atomic
def submit_course_for_review(*, course, user):
    if not can_submit_course_for_review(user, course):
        raise PermissionError("You are not allowed to submit this course for review.")

    course.approval_status = Course.APPROVAL_PENDING
    course.submitted_at = timezone.now()
    course.reviewed_at = None
    course.reviewed_by = None
    course.review_notes = ""
    course.is_published = False
    course.save(update_fields=[
        "approval_status", "submitted_at", "reviewed_at", "reviewed_by",
        "review_notes", "is_published", "updated_at",
    ])

    creator_name = course.created_by.get_username() if course.created_by else "Unknown User"
    _notify_admins(
        title="New Course Awaiting Review",
        message=f'Course "{course.title}" has been submitted for review by {creator_name}.',
    )
    return course


@transaction.atomic
def approve_course(*, course, admin_user):
    if not can_approve_course(admin_user, course):
        raise PermissionError("You are not allowed to approve this course.")

    course.approval_status = Course.APPROVAL_APPROVED
    course.reviewed_by = admin_user
    course.reviewed_at = timezone.now()
    course.review_notes = ""
    course.is_published = False
    course.save(update_fields=[
        "approval_status", "reviewed_by", "reviewed_at", "review_notes",
        "is_published", "updated_at",
    ])

    _notify_course_owner(
        course=course,
        title="Course Approved",
        message=f'Your course "{course.title}" has been approved by the administrator. It can now be published.',
    )
    return course


@transaction.atomic
def request_course_changes(*, course, admin_user, notes):
    if not can_request_changes(admin_user, course):
        raise PermissionError("You are not allowed to request changes for this course.")

    notes = (notes or "").strip()
    if not notes:
        raise ValueError("Review notes are required when requesting changes.")

    course.approval_status = Course.APPROVAL_CHANGES
    course.reviewed_by = admin_user
    course.reviewed_at = timezone.now()
    course.review_notes = notes
    course.is_published = False
    course.save(update_fields=[
        "approval_status", "reviewed_by", "reviewed_at", "review_notes",
        "is_published", "updated_at",
    ])

    _notify_course_owner(
        course=course,
        title="Changes Required for Your Course",
        message=f'Your course "{course.title}" requires changes before it can be approved.\n\nAdministrator feedback:\n{notes}',
    )
    return course


@transaction.atomic
def reject_course(*, course, admin_user, notes):
    if not can_reject_course(admin_user, course):
        raise PermissionError("You are not allowed to reject this course.")

    notes = (notes or "").strip()
    if not notes:
        raise ValueError("Rejection reason is required.")

    course.approval_status = Course.APPROVAL_REJECTED
    course.reviewed_by = admin_user
    course.reviewed_at = timezone.now()
    course.review_notes = notes
    course.is_published = False
    course.is_public = False
    course.save(update_fields=[
        "approval_status", "reviewed_by", "reviewed_at", "review_notes",
        "is_published", "is_public", "updated_at",
    ])

    _notify_course_owner(
        course=course,
        title="Course Rejected",
        message=f'Your course "{course.title}" has been rejected.\n\nAdministrator reason:\n{notes}',
    )
    return course


@transaction.atomic
def publish_course(*, course, user):
    """Publish an approved course; publication is restricted to platform admins."""
    if not can_publish_course(user, course):
        raise PermissionError("You are not allowed to publish this course.")

    course.is_published = True
    course.save(update_fields=["is_published", "updated_at"])

    _notify_course_owner(
        course=course,
        title="Course Published",
        message=f'Your course "{course.title}" has been published and is now available to eligible learners.',
    )
    return course


@transaction.atomic
def unpublish_course(*, course, user):
    """Unpublish a course; publication management is restricted to platform admins."""
    if not user or not user.is_authenticated:
        raise PermissionError("Authentication is required.")
    if not user.is_superuser:
        raise PermissionError("You are not allowed to unpublish this course.")

    course.is_published = False
    course.save(update_fields=["is_published", "updated_at"])

    _notify_course_owner(
        course=course,
        title="Course Unpublished",
        message=f'Your course "{course.title}" has been unpublished.',
    )
    return course
