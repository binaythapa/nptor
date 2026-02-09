from django.shortcuts import render
from organizations.permissions import org_admin_required
from courses.models import Course
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from organizations.permissions import org_admin_required
from organizations.models.subscription import OrganizationCourseSubscription
from courses.models import Course
from organizations.models.membership import OrganizationMember
from organizations.models.role import OrganizationRole
from django.db import models
from django.db.models import Q
from django.utils import timezone




from django.db.models import Q
from django.utils import timezone
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone


from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone


@org_admin_required
def org_courses(request):
    org = request.active_org
    now = timezone.now()

    # --------------------------------------------------
    # 1️⃣ Courses owned by the organization
    # --------------------------------------------------
    org_courses_qs = Course.objects.filter(
        organization=org,
        is_published=True,
    )

    # --------------------------------------------------
    # 2️⃣ ORG ADMIN users of this organization
    # --------------------------------------------------
    org_admin_user_ids = OrganizationMember.objects.filter(
        organization=org,
        role=OrganizationRole.ORG_ADMIN,
        is_active=True,
    ).values_list("user_id", flat=True)

    # --------------------------------------------------
    # 3️⃣ Courses subscribed by ORG ADMINS (ACTIVE only)
    # --------------------------------------------------
    subscribed_courses_qs = Course.objects.filter(
        subscriptions__user_id__in=org_admin_user_ids,
        subscriptions__is_active=True,
        is_published=True,
    ).filter(
        Q(subscriptions__expires_at__isnull=True) |
        Q(subscriptions__expires_at__gt=now)
    )

    # --------------------------------------------------
    # 4️⃣ Union of visible courses
    # --------------------------------------------------
    visible_courses = (
        org_courses_qs
        | subscribed_courses_qs
    ).distinct().order_by("title")

    # --------------------------------------------------
    # 5️⃣ Attached courses (ORG-level only)
    # --------------------------------------------------
    attached_course_ids = set(
        OrganizationCourseSubscription.objects.filter(
            organization=org,
            is_active=True,
        ).values_list("course_id", flat=True)
    )

    # --------------------------------------------------
    # 6️⃣ UI context
    # --------------------------------------------------
    courses = [
        {
            "course": course,
            "is_attached": course.id in attached_course_ids,
        }
        for course in visible_courses
    ]

    return render(
        request,
        "organizations/admin/courses/list.html",
        {"courses": courses}
    )



@org_admin_required
def org_course_attach(request, course_id):
    org = request.active_org
    course = get_object_or_404(Course, id=course_id, is_published=True)

    OrganizationCourseSubscription.objects.update_or_create(
        organization=org,
        course=course,
        defaults={"is_active": True},
    )

    messages.success(request, f"{course.title} attached to organization.")
    return redirect("organizations_admin:courses")



@org_admin_required
def org_course_detach(request, course_id):
    org = request.active_org

    sub = OrganizationCourseSubscription.objects.filter(
        organization=org,
        course_id=course_id
    ).first()

    if sub:
        sub.delete()
        messages.success(request, "Course detached successfully.")

    return redirect("organizations_admin:courses")
