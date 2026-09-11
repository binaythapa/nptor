from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Notification
from courses.models import Course, CourseEnrollment
from organizations.models.access_request import OrganizationAccessRequest
from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.permissions import platform_admin_required
from subscriptions.models import Subscription, SubscriptionEntitlement
from quiz.models import Exam, UserExam


User = get_user_model()


@platform_admin_required
def admin_dashboard(request):
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    total_users = User.objects.count()
    active_users = User.objects.filter(last_login__gte=seven_days_ago).count()
    total_orgs = Organization.objects.count()
    active_orgs = Organization.objects.filter(is_active=True).count()
    total_courses = Course.objects.count()
    published_courses = Course.objects.filter(is_published=True).count()
    total_exams = Exam.objects.count()

    paid_subscriptions = Subscription.objects.filter(amount__gt=0)
    total_revenue = paid_subscriptions.aggregate(total=Sum("amount"))["total"] or 0
    revenue_30d = paid_subscriptions.filter(subscribed_at__gte=thirty_days_ago).aggregate(total=Sum("amount"))["total"] or 0

    completed_attempts = UserExam.objects.filter(submitted_at__isnull=False)
    total_attempts = completed_attempts.count()
    avg_score = completed_attempts.aggregate(value=Avg("score"))["value"]
    pending_requests = OrganizationAccessRequest.objects.filter(status=OrganizationAccessRequest.STATUS_PENDING).count()
    pending_course_reviews = Course.objects.filter(approval_status=Course.APPROVAL_PENDING).count()

    recent_activity = Notification.objects.order_by("-created_at")[:8]
    organization_snapshot = (
        Organization.objects.annotate(member_count=Count("members", filter=Q(members__is_active=True)))
        .order_by("-created_at")[:6]
    )

    context = {
        "total_users": total_users,
        "active_users": active_users,
        "new_users": User.objects.filter(date_joined__gte=seven_days_ago).count(),
        "total_orgs": total_orgs,
        "active_orgs": active_orgs,
        "total_courses": total_courses,
        "published_courses": published_courses,
        "total_exams": total_exams,
        "total_revenue": total_revenue,
        "revenue_30d": revenue_30d,
        "total_attempts": total_attempts,
        "avg_score": round(avg_score, 2) if avg_score is not None else 0,
        "pending_requests": pending_requests,
        "pending_course_reviews": pending_course_reviews,
        "recent_activity": recent_activity,
        "organization_snapshot": organization_snapshot,
        "active_members": OrganizationMember.objects.filter(is_active=True).count(),
        "active_entitlements": SubscriptionEntitlement.objects.filter(is_active=True).count(),
        "enrollments": CourseEnrollment.objects.count(),
        "thirty_day_revenue": revenue_30d,
    }
    return render(request, "quiz/admin/admin_dashboard.html", context)
