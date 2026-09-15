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


@org_admin_required
def org_courses(request, slug):
    """Show only resources owned by this organization.

    Platform/public NPTOR resources are intentionally excluded from the
    organization administration workspace. Organization resources are created,
    managed, and assigned by the organization itself; public-resource commerce
    is handled outside this dashboard.
    """
    org = request.organization
    organization_courses = Course.objects.filter(organization=org)
    organization_tracks = ExamTrack.objects.filter(organization=org).order_by("title")
    organization_exams = Exam.objects.filter(organization=org).order_by("title")

    courses = [
        {
            "course": course,
            "is_attached": False,
            "can_edit": True,
        }
        for course in organization_courses.order_by("title")
    ]
    tracks = [
        {
            "track": track,
            "is_attached": False,
            "can_edit": True,
        }
        for track in organization_tracks
    ]
    exams = [
        {
            "exam": exam,
            "can_edit": True,
        }
        for exam in organization_exams
    ]

    return render(
        request,
        "organizations/admin/courses/list.html",
        {
            "courses": courses,
            "tracks": tracks,
            "exams": exams,
            "org": org,
            "organization_subscription": None,
        },
    )


@require_POST
@org_admin_required
def org_course_attach(request, slug, course_id):
    org = request.organization
    course = get_object_or_404(Course, id=course_id, is_published=True)
    if course.organization_id != org.id:
        messages.error(request, "Public/platform courses cannot be attached from the organization workspace.")
        return redirect("organizations_admin:courses", slug=slug)
    messages.info(request, "Organization-owned courses do not require a product attachment.")
    return redirect("organizations_admin:courses", slug=slug)


@require_POST
@org_admin_required
def org_course_detach(request, slug, course_id):
    course = get_object_or_404(Course, id=course_id)
    if course.organization_id != request.organization.id:
        messages.error(request, "Public/platform courses cannot be managed from the organization workspace.")
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
    form = OrganizationCourseForm(
        request.POST or None,
        request.FILES or None,
        organization=org,
    )
    formset = CourseSectionFormSet(
        request.POST or None,
        prefix="sections",
    )

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

    return render(
        request,
        "organizations/admin/courses/create.html",
        {"form": form, "formset": formset, "organization": org},
    )


@org_teacher_required
def org_course_edit(request, slug, pk):
    """Edit private organization-owned course content without commerce fields."""
    org = request.organization
    course = get_object_or_404(Course, id=pk, organization=org)
    if not user_can_manage_owned_content(request.user, org, course):
        raise PermissionDenied("You can only modify courses you created.")

    form = OrganizationCourseForm(
        request.POST or None,
        request.FILES or None,
        instance=course,
        organization=org,
    )
    formset = CourseSectionFormSet(
        request.POST or None,
        instance=course,
        queryset=course.sections.order_by("order"),
        prefix="sections",
    )

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

    return render(
        request,
        "organizations/admin/courses/edit.html",
        {"form": form, "formset": formset, "course": course, "organization": org},
    )


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
        messages.error(request, "Public/platform tracks cannot be attached from the organization workspace.")
        return redirect("organizations_admin:courses", slug=slug)
    messages.info(request, "Organization-owned tracks do not require a product attachment.")
    return redirect("organizations_admin:courses", slug=slug)


@require_POST
@org_admin_required
def org_track_detach(request, slug, pk):
    track = get_object_or_404(ExamTrack, pk=pk)
    if track.organization_id != request.organization.id:
        messages.error(request, "Public/platform tracks cannot be managed from the organization workspace.")
        return redirect("organizations_admin:courses", slug=slug)
    messages.info(request, "Organization-owned tracks are managed directly by the organization.")
    return redirect("organizations_admin:courses", slug=slug)
