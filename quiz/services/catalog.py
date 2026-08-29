from django.db.models import Q
from django.utils.timezone import now

from quiz.models import Exam, ExamTrack, UserExam
from subscriptions.models import (
    Subscription,
    SubscriptionEntitlement,
)
from subscriptions.services.access_service import AccessService


def build_exam_catalog(*, user, courses=None):
    """
    Build the complete exam catalogue for a student.

    Architecture:

        Subscription
              ↓
        SubscriptionEntitlement
              ↓
        AccessService
              ↓
        Exam / ExamTrack

    Rules:

    1. Free exams can be accessed without payment.
    2. Paid exams can be purchased individually.
    3. Track subscription gives access to exams in that track.
    4. Direct exam subscription gives access to that exam.
    5. Prerequisites and level progression can lock an exam.
    6. A paid exam is NOT considered locked merely because
       the student has not purchased it.
    """

    current_time = now()

    # =========================================================
    # VALID SUBSCRIPTIONS
    # =========================================================

    valid_subscriptions = (
        Subscription.objects
        .filter(
            user=user,
            status=Subscription.STATUS_ACTIVE,
            starts_at__lte=current_time,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=current_time)
        )
    )

    # =========================================================
    # PASSED EXAMS
    # =========================================================

    passed_exam_ids = set(
        UserExam.objects
        .filter(
            user=user,
            passed=True,
        )
        .values_list(
            "exam_id",
            flat=True,
        )
    )

    # =========================================================
    # TRACK SUBSCRIPTIONS
    # =========================================================

    track_subscriptions = {}

    track_entitlements = (
        SubscriptionEntitlement.objects
        .select_related(
            "subscription",
            "track",
        )
        .filter(
            subscription__in=valid_subscriptions,
            resource_type=(
                SubscriptionEntitlement.RESOURCE_TRACK
            ),
            track__isnull=False,
            is_active=True,
        )
    )

    for entitlement in track_entitlements:

        track_id = entitlement.track_id

        if track_id not in track_subscriptions:

            track_subscriptions[
                track_id
            ] = entitlement.subscription

    # =========================================================
    # DIRECT EXAM SUBSCRIPTIONS
    # =========================================================

    exam_subscriptions = {}

    exam_entitlements = (
        SubscriptionEntitlement.objects
        .select_related(
            "subscription",
            "exam",
        )
        .filter(
            subscription__in=valid_subscriptions,
            resource_type=(
                SubscriptionEntitlement.RESOURCE_EXAM
            ),
            exam__isnull=False,
            is_active=True,
        )
    )

    for entitlement in exam_entitlements:

        exam_id = entitlement.exam_id

        if exam_id not in exam_subscriptions:

            exam_subscriptions[
                exam_id
            ] = entitlement.subscription

    # =========================================================
    # TRACKS
    # =========================================================

    tracks = (
        ExamTrack.objects
        .filter(
            is_active=True,
        )
        .prefetch_related(
            "exams",
            "exams__prerequisite_exams",
        )
        .order_by(
            "title",
        )
    )

    track_map = {}

    # =========================================================
    # TRACK PROCESSING
    # =========================================================

    for track in tracks:

        exams = list(
            track.exams
            .filter(
                is_published=True,
            )
            .order_by(
                "level",
                "title",
            )
        )

        if not exams:
            continue

        # -----------------------------------------------------
        # TRACK SUBSCRIPTION
        # -----------------------------------------------------

        track_subscription = (
            track_subscriptions.get(
                track.id
            )
        )

        is_track_subscribed = (
            track_subscription is not None
            and track_subscription.is_valid()
        )

        # -----------------------------------------------------
        # TRACK ACCESS
        # -----------------------------------------------------

        has_track_access = (
            AccessService.has_access(
                student=user,
                resource_type=(
                    AccessService.RESOURCE_TRACK
                ),
                resource=track,
            )
        )

        items = []

        # =====================================================
        # EXAMS
        # =====================================================

        for exam in exams:

            locked_reason = None

            # -------------------------------------------------
            # PREREQUISITES
            # -------------------------------------------------

            prerequisites = (
                exam.prerequisite_exams.all()
            )

            missing_prerequisites = [
                prerequisite.title
                for prerequisite in prerequisites
                if prerequisite.id
                not in passed_exam_ids
            ]

            if missing_prerequisites:

                locked_reason = (
                    "Pass prerequisite: "
                    + ", ".join(
                        missing_prerequisites
                    )
                )

            # -------------------------------------------------
            # LEVEL REQUIREMENT
            # -------------------------------------------------

            if (
                locked_reason is None
                and exam.level
                and exam.level > 1
            ):

                previous_level_passed = any(
                    previous_exam.level
                    == exam.level - 1
                    and previous_exam.id
                    in passed_exam_ids
                    for previous_exam in exams
                )

                if not previous_level_passed:

                    locked_reason = (
                        f"Pass Level "
                        f"{exam.level - 1} first"
                    )

            # -------------------------------------------------
            # DIRECT EXAM SUBSCRIPTION
            # -------------------------------------------------

            exam_subscription = (
                exam_subscriptions.get(
                    exam.id
                )
            )

            is_exam_subscribed = (
                exam_subscription is not None
                and exam_subscription.is_valid()
            )

            # -------------------------------------------------
            # ACTUAL EXAM ACCESS
            # -------------------------------------------------
            #
            # AccessService determines whether the user
            # currently has access.
            #
            # This may come from:
            #
            #   Direct Exam Access
            #   OR
            #   Track Access
            #
            # -------------------------------------------------

            has_exam_access = (
                AccessService.has_access(
                    student=user,
                    resource_type=(
                        AccessService.RESOURCE_EXAM
                    ),
                    resource=exam,
                )
            )

            # -------------------------------------------------
            # INDIVIDUAL EXAM SUBSCRIPTION
            # -------------------------------------------------
            #
            # Only relevant when the track supports
            # exam-level subscription.
            #
            # -------------------------------------------------

            can_subscribe = (
                track.subscription_scope
                == ExamTrack.EXAM
                and locked_reason is None
                and not has_exam_access
                and not exam.is_free
            )

            # -------------------------------------------------
            # BUY INDIVIDUAL EXAM
            # -------------------------------------------------
            #
            # IMPORTANT:
            #
            # A paid exam can be purchased independently.
            #
            # Track subscription scope must NOT prevent this.
            #
            # Example:
            #
            # Test Track
            #     ├── Buy Full Track
            #     └── Test Exam 2 → Buy Now
            #
            # -------------------------------------------------

            can_buy_exam = (
                not exam.is_free
                and exam.price is not None
                and exam.price > 0
                and locked_reason is None
                and not has_exam_access
            )

            # -------------------------------------------------
            # FREE EXAM
            # -------------------------------------------------

            can_start_free_exam = (
                exam.is_free
                and locked_reason is None
                and not has_exam_access
            )

            # -------------------------------------------------
            # FINAL LOCK
            # -------------------------------------------------
            #
            # IMPORTANT:
            #
            # Lack of payment is NOT a lock.
            #
            # Only prerequisites / progression rules lock
            # the exam.
            #
            # -------------------------------------------------

            is_locked = (
                locked_reason is not None
                and not has_exam_access
            )

            # -------------------------------------------------
            # EXAM ITEM
            # -------------------------------------------------

            items.append(
                {
                    "exam": exam,

                    "duration_minutes": (
                        (exam.duration_seconds or 0)
                        // 60
                    ),

                    "price": exam.price,

                    "currency": (
                        exam.currency
                        or "INR"
                    ),

                    # Direct subscription
                    "is_exam_subscribed": (
                        is_exam_subscribed
                    ),

                    # Actual access
                    "has_exam_access": (
                        has_exam_access
                    ),

                    # Track subscription
                    "is_track_subscribed": (
                        is_track_subscribed
                    ),

                    "track_subscription": (
                        track_subscription
                    ),

                    # Actual track access
                    "has_track_access": (
                        has_track_access
                    ),

                    # Subscription availability
                    "can_subscribe": (
                        can_subscribe
                    ),

                    # Individual purchase
                    "can_buy_exam": (
                        can_buy_exam
                    ),

                    # Free exam
                    "can_start_free_exam": (
                        can_start_free_exam
                    ),

                    # Lock
                    "locked": (
                        is_locked
                    ),

                    "locked_reason": (
                        locked_reason
                    ),

                    # Direct subscription
                    "exam_subscription": (
                        exam_subscription
                    ),
                }
            )

        if items:
            track_map[track] = items

    # =========================================================
    # STANDALONE EXAMS
    # =========================================================
    #
    # Exams without a track must also appear.
    #
    # Example:
    #
    # Test exam2
    #     Price: INR 250
    #     Buy Now
    #
    # =========================================================

    standalone_exam_items = []

    standalone_exams = (
        Exam.objects
        .filter(
            is_published=True,
            track__isnull=True,
        )
        .prefetch_related(
            "prerequisite_exams",
        )
        .order_by(
            "level",
            "title",
        )
    )

    for exam in standalone_exams:

        locked_reason = None

        # -----------------------------------------------------
        # PREREQUISITES
        # -----------------------------------------------------

        prerequisites = (
            exam.prerequisite_exams.all()
        )

        missing_prerequisites = [
            prerequisite.title
            for prerequisite in prerequisites
            if prerequisite.id
            not in passed_exam_ids
        ]

        if missing_prerequisites:

            locked_reason = (
                "Pass prerequisite: "
                + ", ".join(
                    missing_prerequisites
                )
            )

        # -----------------------------------------------------
        # DIRECT EXAM SUBSCRIPTION
        # -----------------------------------------------------

        exam_subscription = (
            exam_subscriptions.get(
                exam.id
            )
        )

        is_exam_subscribed = (
            exam_subscription is not None
            and exam_subscription.is_valid()
        )

        # -----------------------------------------------------
        # ACTUAL ACCESS
        # -----------------------------------------------------

        has_exam_access = (
            AccessService.has_access(
                student=user,
                resource_type=(
                    AccessService.RESOURCE_EXAM
                ),
                resource=exam,
            )
        )

        # -----------------------------------------------------
        # BUY EXAM
        # -----------------------------------------------------

        can_buy_exam = (
            not exam.is_free
            and exam.price is not None
            and exam.price > 0
            and locked_reason is None
            and not has_exam_access
        )

        # -----------------------------------------------------
        # FREE EXAM
        # -----------------------------------------------------

        can_start_free_exam = (
            exam.is_free
            and locked_reason is None
            and not has_exam_access
        )

        # -----------------------------------------------------
        # LOCK
        # -----------------------------------------------------

        is_locked = (
            locked_reason is not None
            and not has_exam_access
        )

        standalone_exam_items.append(
            {
                "exam": exam,

                "duration_minutes": (
                    (exam.duration_seconds or 0)
                    // 60
                ),

                "price": exam.price,

                "currency": (
                    exam.currency
                    or "INR"
                ),

                "is_exam_subscribed": (
                    is_exam_subscribed
                ),

                "has_exam_access": (
                    has_exam_access
                ),

                "is_track_subscribed": False,

                "track_subscription": None,

                "has_track_access": False,

                "can_subscribe": False,

                "can_buy_exam": (
                    can_buy_exam
                ),

                "can_start_free_exam": (
                    can_start_free_exam
                ),

                "locked": (
                    is_locked
                ),

                "locked_reason": (
                    locked_reason
                ),

                "exam_subscription": (
                    exam_subscription
                ),
            }
        )

    # =========================================================
    # COURSES
    # =========================================================

    course_items = []

    if courses is not None:

        subscribed_course_ids = set(
            SubscriptionEntitlement.objects
            .filter(
                subscription__in=valid_subscriptions,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_COURSE
                ),
                course__isnull=False,
                is_active=True,
            )
            .values_list(
                "course_id",
                flat=True,
            )
        )

        for course in courses:

            course_items.append(
                {
                    "course": course,

                    "is_subscribed": (
                        course.id
                        in subscribed_course_ids
                    ),
                }
            )

    # =========================================================
    # RETURN
    # =========================================================

    return {
        "courses": course_items,
        "track_map": track_map,
        "standalone_exams": (
            standalone_exam_items
        ),
    }