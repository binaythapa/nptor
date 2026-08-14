from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.db.models import Count


from courses.models import Course

from courses.services.course_approval import (
    approve_course,
    request_course_changes,
    reject_course,
    publish_course,
    unpublish_course,
)


# ============================================================
# ADMIN ACCESS
# ============================================================

def _require_admin(request):
    """
    Platform-level course moderation is restricted
    to Django superusers.
    """

    if not request.user.is_authenticated:
        return False

    return request.user.is_superuser


# ============================================================
# ADMIN COURSE DASHBOARD
# ============================================================

@login_required
def course_dashboard(request):
    """
    Main administrator course moderation dashboard.

    Displays:

        - Draft courses
        - Pending review
        - Approved courses
        - Changes required
        - Rejected courses
        - Published courses
        - Recent courses
        - Recently submitted courses
    """

    # --------------------------------------------------------
    # ADMIN SECURITY
    # --------------------------------------------------------

    if not _require_admin(request):
        return HttpResponseForbidden(
            "Only platform administrators can access "
            "course moderation."
        )

    # --------------------------------------------------------
    # BASE QUERYSET
    # --------------------------------------------------------

    base_queryset = (
        Course.objects
        .select_related(
            "created_by",
            "organization",
            "category",
            "reviewed_by",
        )
        .annotate(
            total_lessons=Count(
                "sections__lessons",
                distinct=True,
            ),
            total_enrollments=Count(
                "enrollments",
                distinct=True,
            ),
        )
    )

    # --------------------------------------------------------
    # STATUS COUNTS
    # --------------------------------------------------------

    pending_count = (
        base_queryset
        .filter(
            approval_status=Course.APPROVAL_PENDING
        )
        .count()
    )

    approved_count = (
        base_queryset
        .filter(
            approval_status=Course.APPROVAL_APPROVED
        )
        .count()
    )

    changes_count = (
        base_queryset
        .filter(
            approval_status=Course.APPROVAL_CHANGES
        )
        .count()
    )

    rejected_count = (
        base_queryset
        .filter(
            approval_status=Course.APPROVAL_REJECTED
        )
        .count()
    )

    draft_count = (
        base_queryset
        .filter(
            approval_status=Course.APPROVAL_DRAFT
        )
        .count()
    )

    # --------------------------------------------------------
    # PUBLISHED COUNT
    #
    # A course is considered publicly published only when:
    #
    #   approval_status = APPROVED
    #   is_published = True
    #   is_public = True
    # --------------------------------------------------------

    published_count = (
        base_queryset
        .filter(
            approval_status=Course.APPROVAL_APPROVED,
            is_published=True,
            is_public=True,
        )
        .count()
    )

    # --------------------------------------------------------
    # RECENT COURSES
    # --------------------------------------------------------

    recent_courses = (
        base_queryset
        .order_by("-created_at")[:10]
    )

    # --------------------------------------------------------
    # RECENT PENDING COURSES
    # --------------------------------------------------------

    pending_courses = (
        base_queryset
        .filter(
            approval_status=Course.APPROVAL_PENDING
        )
        .order_by(
            "submitted_at"
        )[:10]
    )

    # --------------------------------------------------------
    # TEMPLATE CONTEXT
    # --------------------------------------------------------

    context = {
        # ----------------------------------------------------
        # COUNTS
        # ----------------------------------------------------

        "pending_count": pending_count,
        "approved_count": approved_count,
        "changes_count": changes_count,
        "rejected_count": rejected_count,
        "draft_count": draft_count,
        "published_count": published_count,

        # ----------------------------------------------------
        # STATUS VALUES
        #
        # Used by dashboard filters/links.
        # ----------------------------------------------------

        "draft_status": (
            Course.APPROVAL_DRAFT
        ),

        "pending_status": (
            Course.APPROVAL_PENDING
        ),

        "approved_status": (
            Course.APPROVAL_APPROVED
        ),

        "changes_status": (
            Course.APPROVAL_CHANGES
        ),

        "rejected_status": (
            Course.APPROVAL_REJECTED
        ),

        # ----------------------------------------------------
        # COURSE LISTS
        # ----------------------------------------------------

        "recent_courses": recent_courses,

        "pending_courses": pending_courses,
    }

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render(
        request,
        "courses/admin/dashboard.html",
        context,
    )


# ============================================================
# PENDING COURSES
# ============================================================

@login_required
def pending_courses(request):
    """
    Display all courses currently waiting
    for administrator review.
    """

    # --------------------------------------------------------
    # ADMIN SECURITY
    # --------------------------------------------------------

    if not _require_admin(request):
        return HttpResponseForbidden(
            "Only platform administrators can access "
            "course moderation."
        )

    # --------------------------------------------------------
    # QUERY
    # --------------------------------------------------------

    courses = (
        Course.objects
        .filter(
            approval_status=Course.APPROVAL_PENDING
        )
        .select_related(
            "created_by",
            "organization",
            "category",
            "reviewed_by",
        )
        .annotate(
            total_lessons=Count(
                "sections__lessons",
                distinct=True,
            ),
            total_enrollments=Count(
                "enrollments",
                distinct=True,
            ),
        )
        .order_by(
            "submitted_at"
        )
    )

    return render(
        request,
        "courses/admin/pending_courses.html",
        {
            "courses": courses,
        },
    )


# ============================================================
# ALL COURSES
# ============================================================

@login_required
def all_courses(request):
    """
    Display all courses for administrators.

    Supports optional status filtering:

        ?status=draft
        ?status=pending
        ?status=approved
        ?status=changes_required
        ?status=rejected
    """

    # --------------------------------------------------------
    # ADMIN SECURITY
    # --------------------------------------------------------

    if not _require_admin(request):
        return HttpResponseForbidden(
            "Only platform administrators can access "
            "course moderation."
        )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    status = request.GET.get(
        "status",
        "",
    ).strip()

    # --------------------------------------------------------
    # BASE QUERY
    # --------------------------------------------------------

    courses = (
        Course.objects
        .select_related(
            "created_by",
            "organization",
            "category",
            "reviewed_by",
        )
        .annotate(
            total_lessons=Count(
                "sections__lessons",
                distinct=True,
            ),
            total_enrollments=Count(
                "enrollments",
                distinct=True,
            ),
        )
    )

    # --------------------------------------------------------
    # VALID STATUS FILTER
    # --------------------------------------------------------

    valid_statuses = {
        Course.APPROVAL_DRAFT,
        Course.APPROVAL_PENDING,
        Course.APPROVAL_APPROVED,
        Course.APPROVAL_CHANGES,
        Course.APPROVAL_REJECTED,
    }

    if status in valid_statuses:

        courses = courses.filter(
            approval_status=status
        )

    # --------------------------------------------------------
    # ORDER
    # --------------------------------------------------------

    courses = courses.order_by(
        "-created_at"
    )

    return render(
        request,
        "courses/admin/all_courses.html",
        {
            "courses": courses,
            "current_status": status,
        },
    )


# ============================================================
# COURSE REVIEW
# ============================================================

@login_required
def review_course(request, slug):
    """
    Display a complete course to the administrator
    for moderation.
    """

    # --------------------------------------------------------
    # ADMIN SECURITY
    # --------------------------------------------------------

    if not _require_admin(request):
        return HttpResponseForbidden(
            "Only platform administrators can review courses."
        )

    # --------------------------------------------------------
    # COURSE
    # --------------------------------------------------------

    course = get_object_or_404(
        Course.objects.select_related(
            "created_by",
            "organization",
            "category",
            "reviewed_by",
        ),
        slug=slug,
    )

    # --------------------------------------------------------
    # SECTIONS + LESSONS
    # --------------------------------------------------------

    sections = (
        course.sections
        .prefetch_related(
            "lessons"
        )
        .order_by(
            "order"
        )
    )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render(
        request,
        "courses/admin/course_review.html",
        {
            "course": course,
            "sections": sections,
        },
    )


# ============================================================
# APPROVE COURSE
# ============================================================

@login_required
def approve_course_view(request, slug):
    """
    Approve a course awaiting review.

    IMPORTANT:

        Approval does NOT publish the course.
    """

    # --------------------------------------------------------
    # ADMIN SECURITY
    # --------------------------------------------------------

    if not _require_admin(request):
        return HttpResponseForbidden(
            "Only platform administrators can approve courses."
        )

    # --------------------------------------------------------
    # POST ONLY
    # --------------------------------------------------------

    if request.method != "POST":
        return HttpResponseForbidden(
            "POST request required."
        )

    # --------------------------------------------------------
    # COURSE
    # --------------------------------------------------------

    course = get_object_or_404(
        Course,
        slug=slug,
    )

    # --------------------------------------------------------
    # APPROVE
    # --------------------------------------------------------

    try:

        approve_course(
            course=course,
            admin_user=request.user,
        )

    except PermissionError as exc:

        return HttpResponseForbidden(
            str(exc)
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "courses:admin-review-course",
            slug=course.slug,
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    messages.success(
        request,
        f'"{course.title}" has been approved.',
    )

    return redirect(
        "courses:admin-review-course",
        slug=course.slug,
    )


# ============================================================
# REQUEST CHANGES
# ============================================================

@login_required
def request_course_changes_view(
    request,
    slug,
):
    """
    Request changes from the course creator.

    Administrator must provide review notes.
    """

    # --------------------------------------------------------
    # ADMIN SECURITY
    # --------------------------------------------------------

    if not _require_admin(request):
        return HttpResponseForbidden(
            "Only platform administrators can request changes."
        )

    # --------------------------------------------------------
    # POST ONLY
    # --------------------------------------------------------

    if request.method != "POST":
        return HttpResponseForbidden(
            "POST request required."
        )

    # --------------------------------------------------------
    # COURSE
    # --------------------------------------------------------

    course = get_object_or_404(
        Course,
        slug=slug,
    )

    # --------------------------------------------------------
    # NOTES
    # --------------------------------------------------------

    notes = request.POST.get(
        "review_notes",
        "",
    ).strip()

    if not notes:

        messages.error(
            request,
            "Please provide feedback before "
            "requesting changes.",
        )

        return redirect(
            "courses:admin-review-course",
            slug=course.slug,
        )

    # --------------------------------------------------------
    # REQUEST CHANGES
    # --------------------------------------------------------

    try:

        request_course_changes(
            course=course,
            admin_user=request.user,
            notes=notes,
        )

    except PermissionError as exc:

        return HttpResponseForbidden(
            str(exc)
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "courses:admin-review-course",
            slug=course.slug,
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    messages.success(
        request,
        f'Changes requested for "{course.title}".',
    )

    return redirect(
        "courses:admin-course-dashboard",
    )


# ============================================================
# REJECT COURSE
# ============================================================

@login_required
def reject_course_view(
    request,
    slug,
):
    """
    Reject a course submission.

    Administrator must provide a rejection reason.
    """

    # --------------------------------------------------------
    # ADMIN SECURITY
    # --------------------------------------------------------

    if not _require_admin(request):
        return HttpResponseForbidden(
            "Only platform administrators can reject courses."
        )

    # --------------------------------------------------------
    # POST ONLY
    # --------------------------------------------------------

    if request.method != "POST":
        return HttpResponseForbidden(
            "POST request required."
        )

    # --------------------------------------------------------
    # COURSE
    # --------------------------------------------------------

    course = get_object_or_404(
        Course,
        slug=slug,
    )

    # --------------------------------------------------------
    # NOTES
    # --------------------------------------------------------

    notes = request.POST.get(
        "review_notes",
        "",
    ).strip()

    if not notes:

        messages.error(
            request,
            "Please provide a rejection reason.",
        )

        return redirect(
            "courses:admin-review-course",
            slug=course.slug,
        )

    # --------------------------------------------------------
    # REJECT
    # --------------------------------------------------------

    try:

        reject_course(
            course=course,
            admin_user=request.user,
            notes=notes,
        )

    except PermissionError as exc:

        return HttpResponseForbidden(
            str(exc)
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "courses:admin-review-course",
            slug=course.slug,
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    messages.success(
        request,
        f'"{course.title}" has been rejected.',
    )

    return redirect(
        "courses:admin-course-dashboard",
    )


# ============================================================
# PUBLISH COURSE
# ============================================================

@login_required
def publish_course_view(
    request,
    slug,
):
    """
    Publish an approved course.

    Publishing is deliberately separated
    from the approval process.
    """

    # --------------------------------------------------------
    # ADMIN SECURITY
    # --------------------------------------------------------

    if not _require_admin(request):
        return HttpResponseForbidden(
            "Only platform administrators can publish courses."
        )

    # --------------------------------------------------------
    # POST ONLY
    # --------------------------------------------------------

    if request.method != "POST":
        return HttpResponseForbidden(
            "POST request required."
        )

    # --------------------------------------------------------
    # COURSE
    # --------------------------------------------------------

    course = get_object_or_404(
        Course,
        slug=slug,
    )

    # --------------------------------------------------------
    # PUBLISH
    # --------------------------------------------------------

    try:

        publish_course(
            course=course,
            admin_user=request.user,
        )

    except PermissionError as exc:

        return HttpResponseForbidden(
            str(exc)
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "courses:admin-review-course",
            slug=course.slug,
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    messages.success(
        request,
        f'"{course.title}" is now published.',
    )

    return redirect(
        "courses:admin-review-course",
        slug=course.slug,
    )


# ============================================================
# UNPUBLISH COURSE
# ============================================================

@login_required
def unpublish_course_view(
    request,
    slug,
):
    """
    Unpublish an existing course.

    Approval remains intact.

    Result:

        approved
        is_published = False
        is_public = False
    """

    # --------------------------------------------------------
    # ADMIN SECURITY
    # --------------------------------------------------------

    if not _require_admin(request):
        return HttpResponseForbidden(
            "Only platform administrators can unpublish courses."
        )

    # --------------------------------------------------------
    # POST ONLY
    # --------------------------------------------------------

    if request.method != "POST":
        return HttpResponseForbidden(
            "POST request required."
        )

    # --------------------------------------------------------
    # COURSE
    # --------------------------------------------------------

    course = get_object_or_404(
        Course,
        slug=slug,
    )

    # --------------------------------------------------------
    # UNPUBLISH
    # --------------------------------------------------------

    try:

        unpublish_course(
            course=course,
            admin_user=request.user,
        )

    except PermissionError as exc:

        return HttpResponseForbidden(
            str(exc)
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    messages.success(
        request,
        f'"{course.title}" has been unpublished.',
    )

    return redirect(
        "courses:admin-review-course",
        slug=course.slug,
    )