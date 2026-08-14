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
)


User = get_user_model()


# ============================================================
# INTERNAL: ADMIN NOTIFICATION
# ============================================================

def _notify_admins(*, title, message):
    """
    Send a notification to all active platform administrators.

    Platform administrators are represented by Django
    superusers.
    """

    admins = User.objects.filter(
        is_superuser=True,
        is_active=True,
    )

    notification = Notification.objects.create(
        title=title,
        message=message,
    )

    if admins.exists():
        notification.recipients.add(
            *admins
        )

    return notification


# ============================================================
# INTERNAL: COURSE OWNER NOTIFICATION
# ============================================================

def _notify_course_owner(
    *,
    course,
    title,
    message,
):
    """
    Send a notification to the user who created the course.
    """

    if not course.created_by:
        return None

    notification = Notification.objects.create(
        title=title,
        message=message,
    )

    notification.recipients.add(
        course.created_by
    )

    return notification


# ============================================================
# SUBMIT COURSE FOR REVIEW
# ============================================================

@transaction.atomic
def submit_course_for_review(
    *,
    course,
    user,
):
    """
    Submit or resubmit a course for administrator review.

    Allowed states:

        DRAFT
        CHANGES_REQUIRED
        REJECTED

    Result:

        PENDING
    """

    if not can_submit_course_for_review(
        user,
        course,
    ):
        raise PermissionError(
            "You are not allowed to submit this course for review."
        )

    # --------------------------------------------------------
    # Update approval state
    # --------------------------------------------------------

    course.approval_status = (
        Course.APPROVAL_PENDING
    )

    course.submitted_at = timezone.now()

    # Clear previous review information
    course.reviewed_at = None
    course.reviewed_by = None
    course.review_notes = ""

    # Never publish automatically
    course.is_published = False

    course.save(
        update_fields=[
            "approval_status",
            "submitted_at",
            "reviewed_at",
            "reviewed_by",
            "review_notes",
            "is_published",
            "updated_at",
        ]
    )

    # --------------------------------------------------------
    # Notify administrators
    # --------------------------------------------------------

    creator_name = (
        course.created_by.get_username()
        if course.created_by
        else "Unknown User"
    )

    _notify_admins(
        title="New Course Awaiting Review",
        message=(
            f'Course "{course.title}" has been '
            f"submitted for review by {creator_name}."
        ),
    )

    return course


# ============================================================
# APPROVE COURSE
# ============================================================

@transaction.atomic
def approve_course(
    *,
    course,
    admin_user,
):
    """
    Approve a course currently awaiting review.

    IMPORTANT:

    Approval does NOT publish the course.

    Result:

        APPROVED
        is_published = False
    """

    if not can_approve_course(
        admin_user,
        course,
    ):
        raise PermissionError(
            "You are not allowed to approve this course."
        )

    # --------------------------------------------------------
    # Update approval state
    # --------------------------------------------------------

    course.approval_status = (
        Course.APPROVAL_APPROVED
    )

    course.reviewed_by = admin_user
    course.reviewed_at = timezone.now()

    course.review_notes = ""

    # Approval does not automatically publish
    course.is_published = False

    course.save(
        update_fields=[
            "approval_status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "is_published",
            "updated_at",
        ]
    )

    # --------------------------------------------------------
    # Notify course owner
    # --------------------------------------------------------

    _notify_course_owner(
        course=course,
        title="Course Approved",
        message=(
            f'Your course "{course.title}" '
            "has been approved by the administrator. "
            "It can now be published."
        ),
    )

    return course


# ============================================================
# REQUEST CHANGES
# ============================================================

@transaction.atomic
def request_course_changes(
    *,
    course,
    admin_user,
    notes,
):
    """
    Request changes to a course.

    Result:

        CHANGES_REQUIRED
    """

    if not can_request_changes(
        admin_user,
        course,
    ):
        raise PermissionError(
            "You are not allowed to request changes "
            "for this course."
        )

    notes = (
        notes or ""
    ).strip()

    if not notes:
        raise ValueError(
            "Review notes are required when requesting changes."
        )

    # --------------------------------------------------------
    # Update course
    # --------------------------------------------------------

    course.approval_status = (
        Course.APPROVAL_CHANGES
    )

    course.reviewed_by = admin_user
    course.reviewed_at = timezone.now()

    course.review_notes = notes

    # Course must not remain published
    course.is_published = False

    course.save(
        update_fields=[
            "approval_status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "is_published",
            "updated_at",
        ]
    )

    # --------------------------------------------------------
    # Notify instructor
    # --------------------------------------------------------

    _notify_course_owner(
        course=course,
        title="Changes Required for Your Course",
        message=(
            f'Your course "{course.title}" '
            "requires changes before it can be approved.\n\n"
            f"Administrator feedback:\n{notes}"
        ),
    )

    return course


# ============================================================
# REJECT COURSE
# ============================================================

@transaction.atomic
def reject_course(
    *,
    course,
    admin_user,
    notes,
):
    """
    Reject a course submission.

    The instructor may edit and resubmit the course
    according to the configured permission workflow.
    """

    if not can_reject_course(
        admin_user,
        course,
    ):
        raise PermissionError(
            "You are not allowed to reject this course."
        )

    notes = (
        notes or ""
    ).strip()

    if not notes:
        raise ValueError(
            "Rejection reason is required."
        )

    # --------------------------------------------------------
    # Update course
    # --------------------------------------------------------

    course.approval_status = (
        Course.APPROVAL_REJECTED
    )

    course.reviewed_by = admin_user
    course.reviewed_at = timezone.now()

    course.review_notes = notes

    course.is_published = False
    course.is_public = False

    course.save(
        update_fields=[
            "approval_status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "is_published",
            "is_public",
            "updated_at",
        ]
    )

    # --------------------------------------------------------
    # Notify instructor
    # --------------------------------------------------------

    _notify_course_owner(
        course=course,
        title="Course Rejected",
        message=(
            f'Your course "{course.title}" '
            "has been rejected.\n\n"
            f"Administrator reason:\n{notes}"
        ),
    )

    return course


# ============================================================
# PUBLISH COURSE
# ============================================================

@transaction.atomic
def publish_course(
    *,
    course,
    admin_user,
):
    """
    Publish an approved course.

    Only a platform administrator can publish.

    The course must already be approved.
    """

    # --------------------------------------------------------
    # Authentication
    # --------------------------------------------------------

    if not admin_user or not admin_user.is_authenticated:
        raise PermissionError(
            "Authentication is required."
        )

    # --------------------------------------------------------
    # Administrator permission
    # --------------------------------------------------------

    if not admin_user.is_superuser:
        raise PermissionError(
            "Only platform administrators can publish courses."
        )

    # --------------------------------------------------------
    # Approval check
    # --------------------------------------------------------

    if not course.is_approved():
        raise ValueError(
            "Only an approved course can be published."
        )

    # --------------------------------------------------------
    # Publish
    # --------------------------------------------------------

    course.is_published = True

    # IMPORTANT:
    #
    # Publishing makes the course available publicly
    # only if is_public is also True.
    #
    # We intentionally do not change is_public here.

    course.save(
        update_fields=[
            "is_published",
            "updated_at",
        ]
    )

    # --------------------------------------------------------
    # Notify instructor
    # --------------------------------------------------------

    _notify_course_owner(
        course=course,
        title="Course Published",
        message=(
            f'Your course "{course.title}" '
            "has been published and is now available "
            "to eligible learners."
        ),
    )

    return course


# ============================================================
# UNPUBLISH COURSE
# ============================================================

@transaction.atomic
def unpublish_course(
    *,
    course,
    admin_user,
):
    """
    Unpublish an existing course.

    This does not remove the approval.
    """

    # --------------------------------------------------------
    # Authentication
    # --------------------------------------------------------

    if not admin_user or not admin_user.is_authenticated:
        raise PermissionError(
            "Authentication is required."
        )

    # --------------------------------------------------------
    # Administrator permission
    # --------------------------------------------------------

    if not admin_user.is_superuser:
        raise PermissionError(
            "Only platform administrators can unpublish courses."
        )

    # --------------------------------------------------------
    # Unpublish
    # --------------------------------------------------------

    course.is_published = False

    course.save(
        update_fields=[
            "is_published",
            "updated_at",
        ]
    )

    # --------------------------------------------------------
    # Notify instructor
    # --------------------------------------------------------

    _notify_course_owner(
        course=course,
        title="Course Unpublished",
        message=(
            f'Your course "{course.title}" '
            "has been unpublished by the administrator."
        ),
    )

    return course