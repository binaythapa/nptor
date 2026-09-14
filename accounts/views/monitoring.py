from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator
from django.db.models import (
    Q,
    Count,
    Exists,
    OuterRef,
    Avg,
    Max,
    F,
    FloatField,
    ExpressionWrapper,
    Case,
    When,
    Value,
    Prefetch,
)
from django.utils.timezone import now

from organizations.models import OrganizationMember
from quiz.models import UserExam

from subscriptions.models import (
    Subscription,
    SubscriptionEntitlement,
)


def is_admin(user):
    return user.is_staff


def active_subscription_queryset(current_time):
    return (
        Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            starts_at__lte=current_time,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=current_time)
        )
        .select_related("plan", "organization")
    )


def organization_membership_prefetch(current_time):
    return Prefetch(
        "organization_memberships",
        queryset=(
            OrganizationMember.objects.filter(is_active=True)
            .select_related("organization")
            .prefetch_related(
                Prefetch(
                    "organization__subscriptions",
                    queryset=active_subscription_queryset(current_time),
                    to_attr="active_subscriptions",
                )
            )
        ),
        to_attr="active_memberships",
    )


@user_passes_test(is_admin)
def user_monitoring(request):
    search_query = request.GET.get("q", "")
    user_scope = request.GET.get("user_scope", "all")
    sort_by = request.GET.get("sort", "date_joined")
    order = request.GET.get("order", "desc")

    if user_scope not in {"all", "public", "organization"}:
        user_scope = "all"

    current_time = now()

    users = User.objects.select_related("profile")

    if user_scope == "organization":
        users = users.filter(
            organization_memberships__is_active=True
        ).distinct()
    elif user_scope == "public":
        users = users.exclude(
            organization_memberships__is_active=True
        ).distinct()

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
        )

    users = users.annotate(
        total_attempts=Count(
            "exam_attempts",
            distinct=True,
        ),
        avg_score=Avg("exam_attempts__score"),
        passed_count=Count(
            "exam_attempts",
            filter=Q(exam_attempts__passed=True),
            distinct=True,
        ),
        last_attempt=Max("exam_attempts__submitted_at"),
        total_course_subs=Count(
            "subscriptions__entitlements",
            filter=Q(
                subscriptions__status=Subscription.STATUS_ACTIVE,
                subscriptions__starts_at__lte=current_time,
                subscriptions__entitlements__resource_type=(
                    SubscriptionEntitlement.RESOURCE_COURSE
                ),
                subscriptions__entitlements__is_active=True,
            ),
            distinct=True,
        ),
    )

    users = users.annotate(
        pass_rate=Case(
            When(
                total_attempts=0,
                then=Value(0.0),
            ),
            default=ExpressionWrapper(
                100.0 * F("passed_count") / F("total_attempts"),
                output_field=FloatField(),
            ),
            output_field=FloatField(),
        )
    )

    active_user_subscription = (
        active_subscription_queryset(current_time)
        .filter(user=OuterRef("pk"))
    )

    active_course_entitlement = (
        SubscriptionEntitlement.objects.filter(
            subscription__user=OuterRef("pk"),
            subscription__status=Subscription.STATUS_ACTIVE,
            subscription__starts_at__lte=current_time,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            is_active=True,
        )
        .filter(
            Q(subscription__expires_at__isnull=True)
            | Q(subscription__expires_at__gt=current_time)
        )
    )

    active_exam_entitlement = (
        SubscriptionEntitlement.objects.filter(
            subscription__user=OuterRef("pk"),
            subscription__status=Subscription.STATUS_ACTIVE,
            subscription__starts_at__lte=current_time,
            resource_type=SubscriptionEntitlement.RESOURCE_EXAM,
            is_active=True,
        )
        .filter(
            Q(subscription__expires_at__isnull=True)
            | Q(subscription__expires_at__gt=current_time)
        )
    )

    active_track_entitlement = (
        SubscriptionEntitlement.objects.filter(
            subscription__user=OuterRef("pk"),
            subscription__status=Subscription.STATUS_ACTIVE,
            subscription__starts_at__lte=current_time,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            is_active=True,
        )
        .filter(
            Q(subscription__expires_at__isnull=True)
            | Q(subscription__expires_at__gt=current_time)
        )
    )

    users = users.annotate(
        has_subscription=Exists(active_user_subscription),
        has_exam_subscription=Exists(active_exam_entitlement),
        has_track_subscription=Exists(active_track_entitlement),
        has_course_subscription=Exists(active_course_entitlement),
    ).prefetch_related(
        Prefetch(
            "subscriptions",
            queryset=active_subscription_queryset(current_time),
            to_attr="active_subscriptions",
        ),
        organization_membership_prefetch(current_time),
    )

    allowed_sort_fields = {
        "username": "username",
        "first_name": "first_name",
        "email": "email",
        "date_joined": "date_joined",
        "last_login": "last_login",
        "total_attempts": "total_attempts",
        "total_course_subs": "total_course_subs",
        "avg_score": "avg_score",
        "pass_rate": "pass_rate",
    }

    if sort_by in allowed_sort_fields:
        sort_field = allowed_sort_fields[sort_by]
        if order == "desc":
            sort_field = f"-{sort_field}"
        users = users.order_by(sort_field)
    else:
        users = users.order_by("-date_joined")

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_attempts_all = UserExam.objects.count()
    avg_score_all = UserExam.objects.aggregate(avg=Avg("score"))["avg"]

    active_exam_subs = (
        SubscriptionEntitlement.objects.filter(
            subscription__user__isnull=False,
            subscription__status=Subscription.STATUS_ACTIVE,
            subscription__starts_at__lte=current_time,
            resource_type=SubscriptionEntitlement.RESOURCE_EXAM,
            is_active=True,
        )
        .filter(
            Q(subscription__expires_at__isnull=True)
            | Q(subscription__expires_at__gt=current_time)
        )
        .count()
    )

    active_track_subs = (
        SubscriptionEntitlement.objects.filter(
            subscription__user__isnull=False,
            subscription__status=Subscription.STATUS_ACTIVE,
            subscription__starts_at__lte=current_time,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            is_active=True,
        )
        .filter(
            Q(subscription__expires_at__isnull=True)
            | Q(subscription__expires_at__gt=current_time)
        )
        .count()
    )

    paginator = Paginator(users, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    for managed_user in page_obj.object_list:
        managed_user.primary_membership = (
            managed_user.active_memberships[0]
            if managed_user.active_memberships
            else None
        )
        managed_user.primary_subscription = (
            managed_user.active_subscriptions[0]
            if managed_user.active_subscriptions
            else None
        )
        managed_user.primary_organization_subscription = None
        for membership in managed_user.active_memberships:
            organization_subscriptions = getattr(
                membership.organization,
                "active_subscriptions",
                [],
            )
            if organization_subscriptions:
                managed_user.primary_organization_subscription = (
                    organization_subscriptions[0]
                )
                break

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "user_scope": user_scope,
        "sort_by": sort_by,
        "order": order,
        "total_users": total_users,
        "active_users": active_users,
        "total_attempts_all": total_attempts_all,
        "avg_score_all": avg_score_all,
        "active_exam_subs": active_exam_subs,
        "active_track_subs": active_track_subs,
    }

    return render(
        request,
        "accounts/admin/user_monitoring.html",
        context,
    )


@user_passes_test(is_admin)
def user_monitoring_detail(request, user_id):
    current_time = now()
    user = get_object_or_404(
        User.objects.select_related("profile"),
        pk=user_id,
    )

    memberships = list(
        OrganizationMember.objects.filter(user=user)
        .select_related("organization")
        .order_by("-is_active", "organization__name")
    )
    organization_ids = [membership.organization_id for membership in memberships]

    entitlement_queryset = SubscriptionEntitlement.objects.select_related(
        "course",
        "track",
        "exam",
    )

    direct_subscriptions = (
        Subscription.objects.filter(user=user)
        .select_related("plan", "granted_by")
        .prefetch_related(
            Prefetch(
                "entitlements",
                queryset=entitlement_queryset,
                to_attr="loaded_entitlements",
            )
        )
    )

    organization_subscriptions = (
        Subscription.objects.filter(organization_id__in=organization_ids)
        .select_related("organization", "plan", "granted_by")
        .prefetch_related(
            Prefetch(
                "entitlements",
                queryset=entitlement_queryset,
                to_attr="loaded_entitlements",
            )
        )
    )

    attempts = UserExam.objects.filter(user=user).select_related("exam").order_by(
        "-submitted_at",
        "-started_at",
    )
    attempt_stats = attempts.aggregate(
        total=Count("id"),
        average=Avg("score"),
        passed=Count("id", filter=Q(passed=True)),
        last=Max("submitted_at"),
    )

    valid_direct_subscriptions = [
        subscription
        for subscription in direct_subscriptions
        if subscription.is_valid()
    ]
    valid_organization_subscriptions = [
        subscription
        for subscription in organization_subscriptions
        if subscription.is_valid()
    ]

    context = {
        "managed_user": user,
        "memberships": memberships,
        "direct_subscriptions": direct_subscriptions,
        "organization_subscriptions": organization_subscriptions,
        "valid_direct_subscriptions": valid_direct_subscriptions,
        "valid_organization_subscriptions": valid_organization_subscriptions,
        "active_subscription_count": (
            len(valid_direct_subscriptions)
            + len(valid_organization_subscriptions)
        ),
        "attempt_stats": attempt_stats,
        "recent_attempts": attempts[:10],
        "current_time": current_time,
    }

    return render(
        request,
        "accounts/admin/user_monitoring_detail.html",
        context,
    )
