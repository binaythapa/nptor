from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from organizations.permissions import org_admin_required
from organizations.models.subscription import OrganizationCourseSubscription
from organizations.models.membership import OrganizationMember
from organizations.models.role import OrganizationRole

from courses.models import Course
from courses.forms import CourseForm

from quiz.models import Exam, ExamTrack


# =====================================================
# COURSES + TRACKS + EXAMS (ORG RESOURCE CENTER)
# =====================================================
@org_admin_required
def org_courses(request, slug):

    org = request.organization
    now = timezone.now()

    # =====================================================
    # COURSES
    # =====================================================

    organization_courses = Course.objects.filter(
        organization=org
    )

    platform_courses = Course.objects.filter(
        owner_type="platform",
        is_published=True
    )

    org_admin_user_ids = OrganizationMember.objects.filter(
        organization=org,
        role=OrganizationRole.ORG_ADMIN,
        is_active=True
    ).values_list("user_id", flat=True)

    subscribed_courses = Course.objects.filter(
        subscriptions__user_id__in=org_admin_user_ids,
        subscriptions__is_active=True
    ).filter(
        Q(subscriptions__expires_at__isnull=True) |
        Q(subscriptions__expires_at__gt=now)
    )

    visible_courses = (
        organization_courses |
        platform_courses |
        subscribed_courses
    ).distinct().order_by("title")

    attached_course_ids = set(
        OrganizationCourseSubscription.objects.filter(
            organization=org,
            course__isnull=False,
            is_active=True
        ).values_list("course_id", flat=True)
    )

    courses = [
        {
            "course": c,
            "is_attached": c.id in attached_course_ids,
            "can_edit": (
                c.organization == org
                or c.created_by == request.user
            )
        }
        for c in visible_courses
    ]

    # =====================================================
    # TRACKS
    # =====================================================

    visible_tracks = ExamTrack.objects.all().order_by("title")

    attached_track_ids = set(
        OrganizationCourseSubscription.objects.filter(
            organization=org,
            track__isnull=False,
            is_active=True
        ).values_list("track_id", flat=True)
    )

    tracks = [
        {
            "track": t,
            "is_attached": t.id in attached_track_ids
        }
        for t in visible_tracks
    ]

    # =====================================================
    # EXAMS
    # =====================================================

    visible_exams = Exam.objects.select_related("track").order_by("title")

    attached_exam_ids = set(
        OrganizationCourseSubscription.objects.filter(
            organization=org,
            exam__isnull=False,
            is_active=True
        ).values_list("exam_id", flat=True)
    )

    exams = [
        {
            "exam": e,
            "is_attached": e.id in attached_exam_ids
        }
        for e in visible_exams
    ]

    return render(
        request,
        "organizations/admin/courses/list.html",
        {
            "courses": courses,
            "tracks": tracks,
            "exams": exams,
            "org": org
        }
    )


# =====================================================
# ATTACH COURSE
# =====================================================

@org_admin_required
def org_course_attach(request, slug, course_id):

    org = request.organization

    course = get_object_or_404(
        Course,
        id=course_id,
        is_published=True
    )

    OrganizationCourseSubscription.objects.update_or_create(
        organization=org,
        course=course,
        defaults={"is_active": True},
    )

    messages.success(
        request,
        f"{course.title} attached to organization."
    )

    return redirect("organizations_admin:courses", slug=slug)


# =====================================================
# DETACH COURSE
# =====================================================

@org_admin_required
def org_course_detach(request, slug, course_id):

    org = request.organization

    sub = OrganizationCourseSubscription.objects.filter(
        organization=org,
        course_id=course_id
    ).first()

    if sub:
        sub.delete()
        messages.success(request, "Course detached successfully.")

    return redirect("organizations_admin:courses", slug=slug)


# =====================================================
# ORGANIZATION OWNED COURSES
# =====================================================

@org_admin_required
def org_course_list(request, slug):

    org = request.organization

    courses = Course.objects.filter(
        organization=org
    ).order_by("-created_at")

    return render(
        request,
        "organizations/admin/courses/crud_list.html",
        {
            "courses": courses,
            "org": org,
        }
    )


# =====================================================
# CREATE COURSE
# =====================================================

@org_admin_required
def org_course_create(request, slug):

    org = request.organization

    if request.method == "POST":

        form = CourseForm(request.POST, request.FILES)

        if form.is_valid():

            course = form.save(commit=False)
            course.owner_type = "organization"
            course.organization = org
            course.created_by = request.user
            course.save()

            form.save_m2m()

            messages.success(request, "Course created successfully.")

            return redirect("organizations_admin:org_course_list", slug=slug)

    else:
        form = CourseForm()

    return render(
        request,
        "organizations/admin/courses/create.html",
        {
            "form": form,
            "org": org
        }
    )


# =====================================================
# EDIT COURSE
# =====================================================

@org_admin_required
def org_course_edit(request, slug, pk):

    org = request.organization

    course = get_object_or_404(Course, id=pk)

    if course.organization != org and course.created_by != request.user:
        messages.error(request, "You cannot edit this course.")
        return redirect("organizations_admin:org_course_list", slug=slug)

    if request.method == "POST":

        form = CourseForm(request.POST, request.FILES, instance=course)

        if form.is_valid():

            form.save()

            messages.success(request, "Course updated successfully.")

            return redirect("organizations_admin:org_course_list", slug=slug)

    else:
        form = CourseForm(instance=course)

    return render(
        request,
        "organizations/admin/courses/edit.html",
        {
            "form": form,
            "course": course,
            "org": org
        }
    )


# =====================================================
# DELETE COURSE
# =====================================================

@org_admin_required
def org_course_delete(request, slug, pk):

    org = request.organization

    course = get_object_or_404(Course, id=pk)

    if course.organization != org and course.created_by != request.user:
        messages.error(request, "You cannot delete this course.")
        return redirect("organizations_admin:org_course_list", slug=slug)

    course.delete()

    messages.success(request, "Course deleted successfully.")

    return redirect("organizations_admin:org_course_list", slug=slug)


# =====================================================
# TRACK ATTACH / DETACH
# =====================================================
@org_admin_required
def org_track_attach(request, slug, pk):

    org = request.organization

    track = get_object_or_404(ExamTrack, pk=pk)

    OrganizationCourseSubscription.objects.update_or_create(
        organization=org,
        track=track,
        defaults={"is_active": True}
    )

    messages.success(request, "Track attached successfully.")

    return redirect("organizations_admin:courses", slug=slug)



@org_admin_required
def org_track_detach(request, slug, pk):

    org = request.organization

    sub = OrganizationCourseSubscription.objects.filter(
        organization=org,
        track_id=pk
    ).first()

    if sub:
        sub.delete()

    messages.success(request, "Track detached successfully.")

    return redirect("organizations_admin:courses", slug=slug)



# =====================================================
# EXAM ATTACH / DETACH
# =====================================================
@org_admin_required
def org_exam_attach(request, slug, pk):

    org = request.organization

    exam = get_object_or_404(Exam, pk=pk)

    OrganizationCourseSubscription.objects.update_or_create(
        organization=org,
        exam=exam,
        defaults={"is_active": True}
    )

    messages.success(request, "Exam attached successfully.")

    return redirect("organizations_admin:courses", slug=slug)



@org_admin_required
def org_exam_detach(request, slug, pk):

    org = request.organization

    sub = OrganizationCourseSubscription.objects.filter(
        organization=org,
        exam_id=pk
    ).first()

    if sub:
        sub.delete()

    messages.success(request, "Exam detached successfully.")

    return redirect("organizations_admin:courses", slug=slug)