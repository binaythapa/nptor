from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from organizations.permissions import org_admin_required
from courses.forms import CourseForm
from courses.models import Course
from quiz.models import Exam, ExamTrack
from subscriptions.models import Subscription, SubscriptionEntitlement


def get_active_organization_subscription(organization):
    now = timezone.now()
    return (
        Subscription.objects
        .filter(
            organization=organization,
            status=Subscription.STATUS_ACTIVE,
            starts_at__lte=now,
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .order_by("-created_at")
        .first()
    )


def organization_has_entitlement(organization, resource_type, resource_id):
    subscription = get_active_organization_subscription(organization)
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
    return SubscriptionEntitlement.objects.filter(**filters).exists()


def create_resource_entitlement(organization, resource_type, resource):
    subscription = get_active_organization_subscription(organization)
    if not subscription:
        raise ValueError(
            "The organization does not have an active subscription. "
            "Create an organization subscription before attaching resources."
        )

    filters = {"subscription": subscription, "resource_type": resource_type}
    if resource_type == SubscriptionEntitlement.RESOURCE_COURSE:
        filters["course"] = resource
    elif resource_type == SubscriptionEntitlement.RESOURCE_TRACK:
        filters["track"] = resource
    elif resource_type == SubscriptionEntitlement.RESOURCE_EXAM:
        filters["exam"] = resource
    else:
        raise ValueError("Invalid resource type.")

    entitlement = SubscriptionEntitlement.objects.filter(**filters).first()
    if entitlement:
        if not entitlement.is_active:
            entitlement.is_active = True
            entitlement.save(update_fields=["is_active", "updated_at"])
            return entitlement, True
        return entitlement, False

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


def deactivate_resource_entitlement(organization, resource_type, resource_id):
    subscription = get_active_organization_subscription(organization)
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
    entitlement = SubscriptionEntitlement.objects.filter(**filters).first()
    if not entitlement:
        return False
    entitlement.is_active = False
    entitlement.save(update_fields=["is_active", "updated_at"])
    return True


def _platform_or_organization_resource(resource, organization):
    """Return whether a resource may be attached to this organization."""
    return resource.organization_id is None or resource.organization_id == organization.id


def _mutable_course_state(course):
    return course.approval_status in (
        Course.APPROVAL_DRAFT,
        Course.APPROVAL_CHANGES,
        Course.APPROVAL_REJECTED,
    )


@org_admin_required
def org_courses(request, slug):
    org = request.organization
    organization_courses = Course.objects.filter(organization=org)
    platform_courses = Course.objects.filter(
        owner_type=Course.OWNER_PLATFORM,
        is_published=True,
    )
    active_subscription = get_active_organization_subscription(org)
    subscribed_course_ids = set()
    if active_subscription:
        subscribed_course_ids = set(
            SubscriptionEntitlement.objects.filter(
                subscription=active_subscription,
                resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
                is_active=True,
                course__isnull=False,
            ).values_list("course_id", flat=True)
        )
    subscribed_courses = Course.objects.filter(id__in=subscribed_course_ids)
    visible_courses = (organization_courses | platform_courses | subscribed_courses).distinct().order_by("title")
    courses = [
        {
            "course": course,
            "is_attached": course.id in subscribed_course_ids,
            "can_edit": course.organization_id == org.id,
        }
        for course in visible_courses
    ]

    visible_tracks = ExamTrack.objects.filter(
        Q(organization=org) | Q(organization__isnull=True)
    ).order_by("title")
    subscribed_track_ids = set()
    if active_subscription:
        subscribed_track_ids = set(
            SubscriptionEntitlement.objects.filter(
                subscription=active_subscription,
                resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
                is_active=True,
                track__isnull=False,
            ).values_list("track_id", flat=True)
        )
    tracks = [{"track": track, "is_attached": track.id in subscribed_track_ids} for track in visible_tracks]

    visible_exams = Exam.objects.filter(
        Q(organization=org) | Q(organization__isnull=True)
    ).select_related("track").order_by("title")
    subscribed_exam_ids = set()
    if active_subscription:
        subscribed_exam_ids = set(
            SubscriptionEntitlement.objects.filter(
                subscription=active_subscription,
                resource_type=SubscriptionEntitlement.RESOURCE_EXAM,
                is_active=True,
                exam__isnull=False,
            ).values_list("exam_id", flat=True)
        )
    exams = [{"exam": exam, "is_attached": exam.id in subscribed_exam_ids} for exam in visible_exams]

    return render(
        request,
        "organizations/admin/courses/list.html",
        {
            "courses": courses,
            "tracks": tracks,
            "exams": exams,
            "org": org,
            "organization_subscription": active_subscription,
        },
    )


@require_POST
@org_admin_required
def org_course_attach(request, slug, course_id):
    org = request.organization
    course = get_object_or_404(Course, id=course_id, is_published=True)
    if not _platform_or_organization_resource(course, org):
        messages.error(request, "You cannot attach a resource owned by another organization.")
        return redirect("organizations_admin:courses", slug=slug)
    try:
        _, created = create_resource_entitlement(
            organization=org,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            resource=course,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("organizations_admin:courses", slug=slug)
    if created:
        messages.success(request, f"{course.title} attached to organization.")
    else:
        messages.info(request, f"{course.title} is already attached.")
    return redirect("organizations_admin:courses", slug=slug)


@require_POST
@org_admin_required
def org_course_detach(request, slug, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not _platform_or_organization_resource(course, request.organization):
        messages.error(request, "You cannot detach a resource owned by another organization.")
        return redirect("organizations_admin:courses", slug=slug)
    success = deactivate_resource_entitlement(
        organization=request.organization,
        resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
        resource_id=course_id,
    )
    messages.success(request, "Course detached successfully.") if success else messages.info(request, "Course was not attached.")
    return redirect("organizations_admin:courses", slug=slug)


@org_admin_required
def org_course_list(request, slug):
    org = request.organization
    courses = Course.objects.filter(organization=org).order_by("-created_at")
    return render(request, "organizations/admin/courses/crud_list.html", {"courses": courses, "org": org})


@org_admin_required
def org_course_create(request, slug):
    org = request.organization
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, organization=org)
        if form.is_valid():
            course = form.save(commit=False)
            course.owner_type = Course.OWNER_ORGANIZATION
            course.organization = org
            course.created_by = request.user
            course.is_published = False
            course.save()
            form.save_m2m()
            messages.success(request, "Course created successfully.")
            return redirect("organizations_admin:org_course_list", slug=slug)
    else:
        form = CourseForm(organization=org)
    return render(request, "organizations/admin/courses/create.html", {"form": form, "org": org})


@org_admin_required
def org_course_edit(request, slug, pk):
    org = request.organization
    course = get_object_or_404(Course, id=pk, organization=org)
    if not _mutable_course_state(course):
        return HttpResponseForbidden("Course cannot be modified in its current approval state.")
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=course, organization=org)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.is_published = False
            updated.save()
            form.save_m2m()
            messages.success(request, "Course updated successfully.")
            return redirect("organizations_admin:org_course_list", slug=slug)
    else:
        form = CourseForm(instance=course, organization=org)
    return render(request, "organizations/admin/courses/edit.html", {"form": form, "course": course, "org": org})


@require_POST
@org_admin_required
def org_course_delete(request, slug, pk):
    course = get_object_or_404(Course, id=pk, organization=request.organization)
    if not _mutable_course_state(course):
        return HttpResponseForbidden("Course cannot be deleted in its current approval state.")
    course.delete()
    messages.success(request, "Course deleted successfully.")
    return redirect("organizations_admin:org_course_list", slug=slug)


@require_POST
@org_admin_required
def org_track_attach(request, slug, pk):
    org = request.organization
    track = get_object_or_404(ExamTrack, pk=pk)
    if not _platform_or_organization_resource(track, org):
        messages.error(request, "You cannot attach a resource owned by another organization.")
        return redirect("organizations_admin:courses", slug=slug)
    try:
        _, created = create_resource_entitlement(org, SubscriptionEntitlement.RESOURCE_TRACK, track)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("organizations_admin:courses", slug=slug)
    messages.success(request, "Track attached successfully.") if created else messages.info(request, "Track is already attached.")
    return redirect("organizations_admin:courses", slug=slug)


@require_POST
@org_admin_required
def org_track_detach(request, slug, pk):
    track = get_object_or_404(ExamTrack, pk=pk)
    if not _platform_or_organization_resource(track, request.organization):
        messages.error(request, "You cannot detach a resource owned by another organization.")
        return redirect("organizations_admin:courses", slug=slug)
    success = deactivate_resource_entitlement(request.organization, SubscriptionEntitlement.RESOURCE_TRACK, pk)
    messages.success(request, "Track detached successfully.") if success else messages.info(request, "Track was not attached.")
    return redirect("organizations_admin:courses", slug=slug)


@require_POST
@org_admin_required
def org_exam_attach(request, slug, pk):
    org = request.organization
    exam = get_object_or_404(Exam, pk=pk)
    if not _platform_or_organization_resource(exam, org):
        messages.error(request, "You cannot attach a resource owned by another organization.")
        return redirect("organizations_admin:courses", slug=slug)
    try:
        _, created = create_resource_entitlement(org, SubscriptionEntitlement.RESOURCE_EXAM, exam)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("organizations_admin:courses", slug=slug)
    messages.success(request, "Exam attached successfully.") if created else messages.info(request, "Exam is already attached.")
    return redirect("organizations_admin:courses", slug=slug)


@require_POST
@org_admin_required
def org_exam_detach(request, slug, pk):
    exam = get_object_or_404(Exam, pk=pk)
    if not _platform_or_organization_resource(exam, request.organization):
        messages.error(request, "You cannot detach a resource owned by another organization.")
        return redirect("organizations_admin:courses", slug=slug)
    success = deactivate_resource_entitlement(request.organization, SubscriptionEntitlement.RESOURCE_EXAM, pk)
    messages.success(request, "Exam detached successfully.") if success else messages.info(request, "Exam was not attached.")
    return redirect("organizations_admin:courses", slug=slug)