from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from organizations.forms.content import OrganizationCourseForm
from organizations.permissions import org_admin_required, org_teacher_required
from organizations.services.content_permissions import user_can_manage_owned_content
from organizations.services.public_resource_subscriptions import (
    PublicResourceSubscriptionError,
    subscribe_organization_to_public_resource,
)
from courses.forms import CourseSectionFormSet
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


def _public_course_products():
    return (
        Course.objects
        .filter(
            organization__isnull=True,
            owner_type=Course.OWNER_PLATFORM,
            approval_status=Course.APPROVAL_APPROVED,
            is_published=True,
            is_public=True,
        )
        .prefetch_related("subscription_plans")
        .order_by("title")
    )


def _public_track_products():
    return (
        ExamTrack.objects
        .filter(
            organization__isnull=True,
            is_active=True,
        )
        .prefetch_related("subscription_plans")
        .order_by("title")
    )


@org_admin_required
def org_courses(request, slug):
    """Show organization-owned resources and public resources subscribed by the organization."""
    org = request.organization
    organization_courses = Course.objects.filter(organization=org)
    organization_tracks = ExamTrack.objects.filter(organization=org).order_by("title")
    organization_exams = Exam.objects.filter(organization=org).order_by("title")

    courses = [
        {"course": course, "is_attached": False, "can_edit": True}
        for course in organization_courses.order_by("title")
    ]
    tracks = [
        {"track": track, "is_attached": False, "can_edit": True}
        for track in organization_tracks
    ]
    exams = [
        {"exam": exam, "can_edit": True}
        for exam in organization_exams
    ]

    active_subscription = get_active_organization_subscription(org)
    subscribed_course_ids = set()
    subscribed_track_ids = set()
    if active_subscription:
        subscribed_course_ids = set(
            SubscriptionEntitlement.objects.filter(
                subscription=active_subscription,
                resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
                is_active=True,
            ).values_list("course_id", flat=True)
        )
        subscribed_track_ids = set(
            SubscriptionEntitlement.objects.filter(
                subscription=active_subscription,
                resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
                is_active=True,
            ).values_list("track_id", flat=True)
        )

    public_courses = [
        {"course": course, "subscribed": course.id in subscribed_course_ids}
        for course in _public_course_products()
    ]
    public_tracks = [
        {"track": track, "subscribed": track.id in subscribed_track_ids}
        for track in _public_track_products()
    ]

    return render(
        request,
        "organizations/admin/courses/list.html",
        {
            "courses": courses,
            "tracks": tracks,
            "exams": exams,
            "public_courses": public_courses,
            "public_tracks": public_tracks,
            "org": org,
            "organization_subscription": active_subscription,
        },
    )


@require_POST
@org_admin_required
def org_public_course_subscribe(request, slug, course_id):
    org = request.organization
    plan_id = request.POST.get("plan_id")
    try:
        _, _, created = subscribe_organization_to_public_resource(
            organization=org,
            actor=request.user,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            resource_id=course_id,
            plan_id=plan_id,
        )
    except PublicResourceSubscriptionError as exc:
        messages.error(request, str(exc))
        return redirect("organizations_admin:courses", slug=slug)
    messages.success(
        request,
        "Public course subscription created." if created else "Organization already has an active subscription for this course.",
    )
    return redirect("organizations_admin:courses", slug=slug)


@require_POST
@org_admin_required
def org_public_track_subscribe(request, slug, track_id):
    org = request.organization
    plan_id = request.POST.get("plan_id")
    try:
        _, _, created = subscribe_organization_to_public_resource(
            organization=org,
            actor=request.user,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            resource_id=track_id,
            plan_id=plan_id,
        )
    except PublicResourceSubscriptionError as exc:
        messages.error(request, str(exc))
        return redirect("organizations_admin:courses", slug=slug)
    messages.success(
        request,
        "Public track subscription created." if created else "Organization already has an active subscription for this track.",
    )
    return redirect("organizations_admin:courses", slug=slug)


@require_POST
@org_admin_required
def org_course_attach(request, slug, course_id):
    org = request.organization
    course = get_object_or_404(Course, id=course_id, is_published=True)
    if course.organization_id != org.id:
        messages.error(request, "Public/platform courses must be subscribed to before assignment.")
        return redirect("organizations_admin:courses", slug=slug)
    messages.info(request, "Organization-owned courses do not require a product attachment.")
    return redirect("organizations_admin:courses", slug=slug)


@require_POST
@org_admin_required
def org_course_detach(request, slug, course_id):
    course = get_object_or_404(Course, id=course_id)
    if course.organization_id != request.organization.id:
        messages.error(request, "Public/platform courses are managed through their organization subscription.")
        return redirect("organizations_admin:courses", slug=slug)
    messages.info(request, "Organization-owned courses are managed directly by the organization.")
    return redirect("organizations_admin:courses", slug=slug)


@org_teacher_required
def org_course_list(request, slug):
    org = request.organization
    courses = Course.objects.filter(organization=org).order_by("-created_at")
    return render(request, "organizations/admin/courses/crud_list.html", {"courses": courses, "org": org})


@org_teacher_required
def org_course_create(request, slug):
    """Create private organization-owned course content without commerce fields."""
    org = request.organization
    form = OrganizationCourseForm(request.POST or None, request.FILES or None, organization=org)
    formset = CourseSectionFormSet(request.POST or None, prefix="sections")

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            course = form.save(commit=False)
            course.created_by = request.user
            course.save()
            form.save_m2m()
            sections = formset.save(commit=False)
            for index, section in enumerate(sections, start=1):
                section.course = course
                if not section.order:
                    section.order = index
                section.save()
        messages.success(request, f'Course "{course.title}" created for {org.name}.')
        return redirect("organizations_admin:org_course_list", slug=slug)

    return render(request, "organizations/admin/courses/create.html", {"form": form, "formset": formset, "organization": org})


@org_teacher_required
def org_course_edit(request, slug, pk):
    """Edit private organization-owned course content without commerce fields."""
    org = request.organization
    course = get_object_or_404(Course, id=pk, organization=org)
    if not user_can_manage_owned_content(request.user, org, course):
        raise PermissionDenied("You can only modify courses you created.")

    form = OrganizationCourseForm(request.POST or None, request.FILES or None, instance=course, organization=org)
    formset = CourseSectionFormSet(request.POST or None, instance=course, queryset=course.sections.order_by("order"), prefix="sections")

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            course = form.save(commit=False)
            course.created_by = course.created_by or request.user
            course.save()
            form.save_m2m()
            sections = formset.save(commit=False)
            for section in sections:
                section.course = course
                section.save()
            for obj in formset.deleted_objects:
                obj.delete()
        messages.success(request, f'Course "{course.title}" updated.')
        return redirect("organizations_admin:org_course_list", slug=slug)

    return render(request, "organizations/admin/courses/edit.html", {"form": form, "formset": formset, "course": course, "organization": org})


@require_POST
@org_teacher_required
def org_course_delete(request, slug, pk):
    course = get_object_or_404(Course, id=pk, organization=request.organization)
    if not user_can_manage_owned_content(request.user, request.organization, course):
        raise PermissionDenied("You can only delete courses you created.")
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
    if track.organization_id != org.id:
        messages.error(request, "Public/platform tracks must be subscribed to before assignment.")
        return redirect("organizations_admin:courses", slug=slug)
    messages.info(request, "Organization-owned tracks do not require a product attachment.")
    return redirect("organizations_admin:courses", slug=slug)


@require_POST
@org_admin_required
def org_track_detach(request, slug, pk):
    track = get_object_or_404(ExamTrack, pk=pk)
    if track.organization_id != request.organization.id:
        messages.error(request, "Public/platform tracks are managed directly by the organization.")
        return redirect("organizations_admin:courses", slug=slug)
    messages.info(request, "Organization-owned tracks are managed directly by the organization.")
    return redirect("organizations_admin:courses", slug=slug)
