from django.contrib import messages
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from organizations.permissions import org_admin_required

from courses.forms import CourseForm
from courses.models import Course

from quiz.models import Exam, ExamTrack

from subscriptions.models import (
    Subscription,
    SubscriptionEntitlement,
)


# ============================================================
# SUBSCRIPTION HELPERS
# ============================================================


def get_active_organization_subscription(organization):
    """
    Return the currently valid organization subscription.

    An organization subscription can contain multiple
    resource entitlements.
    """

    now = timezone.now()

    return (
        Subscription.objects
        .filter(
            organization=organization,
            status=Subscription.STATUS_ACTIVE,
            starts_at__lte=now,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=now)
        )
        .order_by("-created_at")
        .first()
    )


def organization_has_entitlement(
    organization,
    resource_type,
    resource_id,
):
    """
    Check whether the organization currently has
    an active entitlement for a resource.
    """

    subscription = get_active_organization_subscription(
        organization
    )

    if not subscription:
        return False

    filters = {
        "subscription": subscription,
        "resource_type": resource_type,
        "is_active": True,
    }

    if resource_type == SubscriptionEntitlement.RESOURCE_COURSE:
        filters["course_id"] = resource_id

    elif resource_type == SubscriptionEntitlement.RESOURCE_TRACK:
        filters["track_id"] = resource_id

    elif resource_type == SubscriptionEntitlement.RESOURCE_EXAM:
        filters["exam_id"] = resource_id

    else:
        return False

    return SubscriptionEntitlement.objects.filter(
        **filters
    ).exists()


def create_resource_entitlement(
    organization,
    resource_type,
    resource,
):
    """
    Attach a resource to the organization's existing
    active subscription.

    Returns:
        (entitlement, created)

    Raises:
        ValueError if the organization has no active subscription.
    """

    subscription = get_active_organization_subscription(
        organization
    )

    if not subscription:
        raise ValueError(
            "The organization does not have an active "
            "subscription. Create an organization subscription "
            "before attaching resources."
        )

    filters = {
        "subscription": subscription,
        "resource_type": resource_type,
    }

    if resource_type == SubscriptionEntitlement.RESOURCE_COURSE:
        filters["course"] = resource

    elif resource_type == SubscriptionEntitlement.RESOURCE_TRACK:
        filters["track"] = resource

    elif resource_type == SubscriptionEntitlement.RESOURCE_EXAM:
        filters["exam"] = resource

    else:
        raise ValueError("Invalid resource type.")

    entitlement = (
        SubscriptionEntitlement.objects
        .filter(**filters)
        .first()
    )

    # Existing entitlement
    if entitlement:

        if not entitlement.is_active:
            entitlement.is_active = True

            entitlement.save(
                update_fields=[
                    "is_active",
                    "updated_at",
                ]
            )

            return entitlement, True

        return entitlement, False

    # New entitlement
    entitlement = SubscriptionEntitlement(
        subscription=subscription,
        resource_type=resource_type,
        is_active=True,
    )

    if resource_type == SubscriptionEntitlement.RESOURCE_COURSE:
        entitlement.course = resource

    elif resource_type == SubscriptionEntitlement.RESOURCE_TRACK:
        entitlement.track = resource

    elif resource_type == SubscriptionEntitlement.RESOURCE_EXAM:
        entitlement.exam = resource

    entitlement.full_clean()
    entitlement.save()

    return entitlement, True


def deactivate_resource_entitlement(
    organization,
    resource_type,
    resource_id,
):
    """
    Deactivate an entitlement without deleting it.

    This preserves subscription history.
    """

    subscription = get_active_organization_subscription(
        organization
    )

    if not subscription:
        return False

    filters = {
        "subscription": subscription,
        "resource_type": resource_type,
        "is_active": True,
    }

    if resource_type == SubscriptionEntitlement.RESOURCE_COURSE:
        filters["course_id"] = resource_id

    elif resource_type == SubscriptionEntitlement.RESOURCE_TRACK:
        filters["track_id"] = resource_id

    elif resource_type == SubscriptionEntitlement.RESOURCE_EXAM:
        filters["exam_id"] = resource_id

    else:
        return False

    entitlement = (
        SubscriptionEntitlement.objects
        .filter(**filters)
        .first()
    )

    if not entitlement:
        return False

    entitlement.is_active = False

    entitlement.save(
        update_fields=[
            "is_active",
            "updated_at",
        ]
    )

    return True


# ============================================================
# COURSES + TRACKS + EXAMS
# ORGANIZATION RESOURCE CENTER
# ============================================================


@org_admin_required
def org_courses(request, slug):
    """
    Organization resource center.

    Shows:

        - Organization-owned courses
        - Public platform courses
        - Courses included in organization subscription
        - Exam tracks
        - Exams

    Resource attachment is based on SubscriptionEntitlement.
    """

    org = request.organization

    # ========================================================
    # COURSES
    # ========================================================

    organization_courses = (
        Course.objects
        .filter(
            organization=org,
        )
    )

    platform_courses = (
        Course.objects
        .filter(
            owner_type=Course.OWNER_PLATFORM,
            is_published=True,
        )
    )

    # --------------------------------------------------------
    # Organization subscription
    # --------------------------------------------------------

    active_subscription = (
        get_active_organization_subscription(org)
    )

    subscribed_course_ids = set()

    if active_subscription:

        subscribed_course_ids = set(
            SubscriptionEntitlement.objects
            .filter(
                subscription=active_subscription,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_COURSE
                ),
                is_active=True,
                course__isnull=False,
            )
            .values_list(
                "course_id",
                flat=True,
            )
        )

    subscribed_courses = Course.objects.filter(
        id__in=subscribed_course_ids
    )

    visible_courses = (
        organization_courses
        | platform_courses
        | subscribed_courses
    ).distinct().order_by("title")

    courses = [
        {
            "course": course,
            "is_attached": (
                course.id in subscribed_course_ids
            ),
            "can_edit": (
                course.organization == org
                or course.created_by == request.user
            ),
        }
        for course in visible_courses
    ]

    # ========================================================
    # TRACKS
    # ========================================================

    visible_tracks = (
        ExamTrack.objects
        .all()
        .order_by("title")
    )

    subscribed_track_ids = set()

    if active_subscription:

        subscribed_track_ids = set(
            SubscriptionEntitlement.objects
            .filter(
                subscription=active_subscription,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_TRACK
                ),
                is_active=True,
                track__isnull=False,
            )
            .values_list(
                "track_id",
                flat=True,
            )
        )

    tracks = [
        {
            "track": track,
            "is_attached": (
                track.id in subscribed_track_ids
            ),
        }
        for track in visible_tracks
    ]

    # ========================================================
    # EXAMS
    # ========================================================

    visible_exams = (
        Exam.objects
        .select_related("track")
        .order_by("title")
    )

    subscribed_exam_ids = set()

    if active_subscription:

        subscribed_exam_ids = set(
            SubscriptionEntitlement.objects
            .filter(
                subscription=active_subscription,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_EXAM
                ),
                is_active=True,
                exam__isnull=False,
            )
            .values_list(
                "exam_id",
                flat=True,
            )
        )

    exams = [
        {
            "exam": exam,
            "is_attached": (
                exam.id in subscribed_exam_ids
            ),
        }
        for exam in visible_exams
    ]

    # ========================================================
    # RESPONSE
    # ========================================================

    return render(
        request,
        "organizations/admin/courses/list.html",
        {
            "courses": courses,
            "tracks": tracks,
            "exams": exams,
            "org": org,
            "organization_subscription": (
                active_subscription
            ),
        },
    )


# ============================================================
# ATTACH COURSE
# ============================================================


@org_admin_required
def org_course_attach(request, slug, course_id):

    org = request.organization

    course = get_object_or_404(
        Course,
        id=course_id,
        is_published=True,
    )

    try:

        entitlement, created = (
            create_resource_entitlement(
                organization=org,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_COURSE
                ),
                resource=course,
            )
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "organizations_admin:courses",
            slug=slug,
        )

    if created:

        messages.success(
            request,
            f"{course.title} attached to organization.",
        )

    else:

        messages.info(
            request,
            f"{course.title} is already attached.",
        )

    return redirect(
        "organizations_admin:courses",
        slug=slug,
    )


# ============================================================
# DETACH COURSE
# ============================================================


@org_admin_required
def org_course_detach(request, slug, course_id):

    org = request.organization

    success = deactivate_resource_entitlement(
        organization=org,
        resource_type=(
            SubscriptionEntitlement.RESOURCE_COURSE
        ),
        resource_id=course_id,
    )

    if success:

        messages.success(
            request,
            "Course detached successfully.",
        )

    else:

        messages.info(
            request,
            "Course was not attached.",
        )

    return redirect(
        "organizations_admin:courses",
        slug=slug,
    )


# ============================================================
# ORGANIZATION OWNED COURSES
# ============================================================


@org_admin_required
def org_course_list(request, slug):

    org = request.organization

    courses = (
        Course.objects
        .filter(
            organization=org,
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "organizations/admin/courses/crud_list.html",
        {
            "courses": courses,
            "org": org,
        },
    )


# ============================================================
# CREATE COURSE
# ============================================================


@org_admin_required
def org_course_create(request, slug):

    org = request.organization

    if request.method == "POST":

        form = CourseForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            course = form.save(
                commit=False
            )

            course.owner_type = (
                Course.OWNER_ORGANIZATION
            )

            course.organization = org
            course.created_by = request.user

            course.save()

            form.save_m2m()

            messages.success(
                request,
                "Course created successfully.",
            )

            return redirect(
                "organizations_admin:org_course_list",
                slug=slug,
            )

    else:

        form = CourseForm()

    return render(
        request,
        "organizations/admin/courses/create.html",
        {
            "form": form,
            "org": org,
        },
    )


# ============================================================
# EDIT COURSE
# ============================================================


@org_admin_required
def org_course_edit(request, slug, pk):

    org = request.organization

    course = get_object_or_404(
        Course,
        id=pk,
    )

    if (
        course.organization != org
        and course.created_by != request.user
    ):

        messages.error(
            request,
            "You cannot edit this course.",
        )

        return redirect(
            "organizations_admin:org_course_list",
            slug=slug,
        )

    if request.method == "POST":

        form = CourseForm(
            request.POST,
            request.FILES,
            instance=course,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Course updated successfully.",
            )

            return redirect(
                "organizations_admin:org_course_list",
                slug=slug,
            )

    else:

        form = CourseForm(
            instance=course,
        )

    return render(
        request,
        "organizations/admin/courses/edit.html",
        {
            "form": form,
            "course": course,
            "org": org,
        },
    )


# ============================================================
# DELETE COURSE
# ============================================================


@org_admin_required
def org_course_delete(request, slug, pk):

    org = request.organization

    course = get_object_or_404(
        Course,
        id=pk,
    )

    if (
        course.organization != org
        and course.created_by != request.user
    ):

        messages.error(
            request,
            "You cannot delete this course.",
        )

        return redirect(
            "organizations_admin:org_course_list",
            slug=slug,
        )

    course.delete()

    messages.success(
        request,
        "Course deleted successfully.",
    )

    return redirect(
        "organizations_admin:org_course_list",
        slug=slug,
    )


# ============================================================
# TRACK ATTACH
# ============================================================


@org_admin_required
def org_track_attach(request, slug, pk):

    org = request.organization

    track = get_object_or_404(
        ExamTrack,
        pk=pk,
    )

    try:

        entitlement, created = (
            create_resource_entitlement(
                organization=org,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_TRACK
                ),
                resource=track,
            )
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "organizations_admin:courses",
            slug=slug,
        )

    if created:

        messages.success(
            request,
            "Track attached successfully.",
        )

    else:

        messages.info(
            request,
            "Track is already attached.",
        )

    return redirect(
        "organizations_admin:courses",
        slug=slug,
    )


# ============================================================
# TRACK DETACH
# ============================================================


@org_admin_required
def org_track_detach(request, slug, pk):

    org = request.organization

    success = deactivate_resource_entitlement(
        organization=org,
        resource_type=(
            SubscriptionEntitlement.RESOURCE_TRACK
        ),
        resource_id=pk,
    )

    if success:

        messages.success(
            request,
            "Track detached successfully.",
        )

    else:

        messages.info(
            request,
            "Track was not attached.",
        )

    return redirect(
        "organizations_admin:courses",
        slug=slug,
    )


# ============================================================
# EXAM ATTACH
# ============================================================


@org_admin_required
def org_exam_attach(request, slug, pk):

    org = request.organization

    exam = get_object_or_404(
        Exam,
        pk=pk,
    )

    try:

        entitlement, created = (
            create_resource_entitlement(
                organization=org,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_EXAM
                ),
                resource=exam,
            )
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "organizations_admin:courses",
            slug=slug,
        )

    if created:

        messages.success(
            request,
            "Exam attached successfully.",
        )

    else:

        messages.info(
            request,
            "Exam is already attached.",
        )

    return redirect(
        "organizations_admin:courses",
        slug=slug,
    )


# ============================================================
# EXAM DETACH
# ============================================================


@org_admin_required
def org_exam_detach(request, slug, pk):

    org = request.organization

    success = deactivate_resource_entitlement(
        organization=org,
        resource_type=(
            SubscriptionEntitlement.RESOURCE_EXAM
        ),
        resource_id=pk,
    )

    if success:

        messages.success(
            request,
            "Exam detached successfully.",
        )

    else:

        messages.info(
            request,
            "Exam was not attached.",
        )

    return redirect(
        "organizations_admin:courses",
        slug=slug,
    )