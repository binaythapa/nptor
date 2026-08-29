from django.db import transaction
from django.utils import timezone

from organizations.models.access import ResourceAccess
from organizations.models.assignment import ResourceAssignment

from subscriptions.models import SubscriptionEntitlement


class AccessService:
    """
    Central service responsible for organization resource access.

    Architecture:

        Subscription
              ↓
        SubscriptionEntitlement
              ↓
        ResourceAssignment
              ↓
        ResourceAccess
              ↓
           Student

    SubscriptionEntitlement
        = what the organization owns

    ResourceAssignment
        = what the organization assigns to a student

    ResourceAccess
        = actual student-level access
    """

    RESOURCE_COURSE = "course"
    RESOURCE_TRACK = "track"
    RESOURCE_EXAM = "exam"

    # =========================================================
    # RESOURCE HELPERS
    # =========================================================

    @staticmethod
    def _resource_filter(resource_type, resource):
        """
        Return the correct resource field for the resource type.
        """

        if not resource:
            raise ValueError("Resource is required.")

        if resource_type == AccessService.RESOURCE_COURSE:
            return {
                "course": resource,
            }

        if resource_type == AccessService.RESOURCE_TRACK:
            return {
                "track": resource,
            }

        if resource_type == AccessService.RESOURCE_EXAM:
            return {
                "exam": resource,
            }

        raise ValueError(
            f"Unsupported resource type: {resource_type}"
        )

    # =========================================================
    # GRANT DIRECT USER / ADMIN ACCESS
    # =========================================================

    @staticmethod
    @transaction.atomic
    def grant_access(
        *,
        user,
        resource_type,
        resource,
        source,
        organization=None,
        subscription=None,
        assignment=None,
        expires_at=None,
    ):
        """
        Grant actual user-level access to a resource.

        Used for:
            - Individual subscription access
            - Administrator granted access
            - Organization access through the generic layer

        Organization assignment logic remains handled by
        grant_student_access().
        """

        if not user:
            raise ValueError("User is required.")

        if not resource:
            raise ValueError("Resource is required.")

        # -----------------------------------------------------
        # Validate resource type
        # -----------------------------------------------------

        if resource_type not in (
            AccessService.RESOURCE_COURSE,
            AccessService.RESOURCE_TRACK,
            AccessService.RESOURCE_EXAM,
        ):
            raise ValueError(
                f"Invalid resource type: {resource_type}"
            )

        # -----------------------------------------------------
        # Organization rules
        # -----------------------------------------------------

        if source == ResourceAccess.SOURCE_ORGANIZATION:

            if not organization:
                raise ValueError(
                    "Organization is required for organization access."
                )

        else:

            if organization:
                raise ValueError(
                    "Organization is only allowed for organization access."
                )

        # -----------------------------------------------------
        # Subscription validation
        # -----------------------------------------------------

        if subscription:

            if not subscription.is_valid():
                raise ValueError(
                    "Subscription is not currently valid."
                )

            if expires_at is None:
                expires_at = subscription.expires_at

        # -----------------------------------------------------
        # Assignment validation
        # -----------------------------------------------------

        if assignment:

            if source != ResourceAccess.SOURCE_ORGANIZATION:
                raise ValueError(
                    "Assignment requires organization access."
                )

            if assignment.student_id != user.id:
                raise ValueError(
                    "Assignment student does not match user."
                )

            if organization and assignment.organization_id != organization.id:
                raise ValueError(
                    "Assignment and organization do not match."
                )

        # -----------------------------------------------------
        # Determine resource field
        # -----------------------------------------------------

        resource_fields = (
            AccessService._resource_filter(
                resource_type,
                resource,
            )
        )

        # -----------------------------------------------------
        # Find existing access
        # -----------------------------------------------------

        filters = {
            "user": user,
            "resource_type": resource_type,
            "source": source,
            "organization": organization,
            **resource_fields,
        }

        access = (
            ResourceAccess.objects
            .select_for_update()
            .filter(**filters)
            .first()
        )

        # -----------------------------------------------------
        # Reactivate existing access
        # -----------------------------------------------------

        if access:

            access.is_active = True
            access.revoked_at = None

            if subscription:
                access.subscription = subscription

            if assignment:
                access.assignment = assignment

            if expires_at is not None:
                access.expires_at = expires_at

            access.full_clean()
            access.save()

            return access, False

        # -----------------------------------------------------
        # Create new access
        # -----------------------------------------------------

        access = ResourceAccess(
            user=user,
            resource_type=resource_type,
            source=source,
            organization=organization,
            subscription=subscription,
            assignment=assignment,
            expires_at=expires_at,
            course=None,
            track=None,
            exam=None,
        )

        for field, value in resource_fields.items():
            setattr(access, field, value)

        access.full_clean()
        access.save()

        return access, True

    # =========================================================
    # ORGANIZATION ENTITLEMENT
    # =========================================================

    @staticmethod
    def get_organization_entitlement(
        organization,
        resource_type,
        resource,
    ):
        """
        Return a valid active entitlement for the organization.

        An organization must have:

        1. Active subscription
        2. Subscription already started
        3. Subscription not expired
        4. Active entitlement
        5. Correct resource
        """

        if not organization:
            return None

        if not resource:
            return None

        filters = {
            "subscription__organization": organization,
            "subscription__status": "active",
            "subscription__starts_at__lte": timezone.now(),
            "is_active": True,
            "resource_type": resource_type,
        }

        filters.update(
            AccessService._resource_filter(
                resource_type,
                resource,
            )
        )

        entitlement = (
            SubscriptionEntitlement.objects
            .select_related("subscription")
            .filter(**filters)
            .first()
        )

        if not entitlement:
            return None

        subscription = entitlement.subscription

        if not subscription.is_valid():
            return None

        return entitlement

    # =========================================================
    # ORGANIZATION RESOURCE CHECK
    # =========================================================

    @staticmethod
    def organization_has_resource(
        organization,
        resource_type,
        resource,
    ):
        """
        Return True when the organization currently owns
        the resource through a valid subscription entitlement.
        """

        return (
            AccessService.get_organization_entitlement(
                organization=organization,
                resource_type=resource_type,
                resource=resource,
            )
            is not None
        )

    # =========================================================
    # GRANT STUDENT ACCESS
    # =========================================================

    @staticmethod
    @transaction.atomic
    def grant_student_access(
        *,
        student,
        organization,
        resource_type,
        resource,
    ):
        """
        Grant a resource to a student.

        Flow:

            Organization Subscription
                    ↓
            SubscriptionEntitlement
                    ↓
            ResourceAssignment
                    ↓
            ResourceAccess

        Existing assignments/access records are reused.
        """

        if not student:
            raise ValueError(
                "Student is required."
            )

        if not organization:
            raise ValueError(
                "Organization is required."
            )

        if not resource:
            raise ValueError(
                "Resource is required."
            )

        # -----------------------------------------------------
        # Validate organization entitlement
        # -----------------------------------------------------

        entitlement = (
            AccessService.get_organization_entitlement(
                organization=organization,
                resource_type=resource_type,
                resource=resource,
            )
        )

        if not entitlement:
            raise ValueError(
                "The organization does not have an active "
                "subscription entitlement for this resource."
            )

        subscription = entitlement.subscription

        # -----------------------------------------------------
        # Resource fields
        # -----------------------------------------------------

        resource_fields = (
            AccessService._resource_filter(
                resource_type,
                resource,
            )
        )

        # -----------------------------------------------------
        # Resource Assignment
        # -----------------------------------------------------

        assignment, assignment_created = (
            ResourceAssignment.objects.get_or_create(
                student=student,
                organization=organization,
                resource_type=resource_type,
                **resource_fields,
            )
        )

        # -----------------------------------------------------
        # Resource Access
        # -----------------------------------------------------

        access = (
            ResourceAccess.objects
            .filter(
                user=student,
                resource_type=resource_type,
                organization=organization,
                source=ResourceAccess.SOURCE_ORGANIZATION,
                **resource_fields,
            )
            .first()
        )

        access_created = access is None

        if access is None:

            access = ResourceAccess(
                user=student,
                resource_type=resource_type,
                source=ResourceAccess.SOURCE_ORGANIZATION,
                organization=organization,
                subscription=subscription,
                assignment=assignment,
                is_active=True,
                expires_at=subscription.expires_at,
                **resource_fields,
            )

        else:

            # Existing access may have been revoked previously.
            # Reactivate it and associate it with the current
            # subscription and assignment.

            access.subscription = subscription
            access.assignment = assignment
            access.is_active = True
            access.expires_at = subscription.expires_at
            access.revoked_at = None
            access.source = (
                ResourceAccess.SOURCE_ORGANIZATION
            )

        # -----------------------------------------------------
        # Validate before saving
        # -----------------------------------------------------

        access.full_clean()
        access.save()

        return {
            "assignment": assignment,
            "assignment_created": assignment_created,
            "access": access,
            "access_created": access_created,
            "entitlement": entitlement,
        }

    # =========================================================
    # REVOKE STUDENT ACCESS
    # =========================================================

    @staticmethod
    @transaction.atomic
    def revoke_student_access(
        *,
        student,
        organization,
        resource_type,
        resource,
    ):
        """
        Revoke student access.

        ResourceAccess is preserved for history.

        ResourceAssignment is removed because the current
        ResourceAssignment model does not have an is_active field.
        """

        if not student:
            raise ValueError(
                "Student is required."
            )

        if not organization:
            raise ValueError(
                "Organization is required."
            )

        if not resource:
            raise ValueError(
                "Resource is required."
            )

        resource_fields = (
            AccessService._resource_filter(
                resource_type,
                resource,
            )
        )

        # -----------------------------------------------------
        # ResourceAccess
        # -----------------------------------------------------

        access_qs = (
            ResourceAccess.objects
            .filter(
                user=student,
                organization=organization,
                resource_type=resource_type,
                source=ResourceAccess.SOURCE_ORGANIZATION,
                **resource_fields,
            )
        )

        access_records = list(
            access_qs
        )

        access_count = 0

        for access in access_records:

            if access.is_active:

                access.revoke()

                access_count += 1

        # -----------------------------------------------------
        # ResourceAssignment
        # -----------------------------------------------------

        assignment_qs = (
            ResourceAssignment.objects
            .filter(
                student=student,
                organization=organization,
                resource_type=resource_type,
                **resource_fields,
            )
        )

        assignment_count, _ = (
            assignment_qs.delete()
        )

        return {
            "access_revoked": access_count > 0,
            "assignment_removed": (
                assignment_count > 0
            ),
        }










    # =========================================================
    # REVOKE DIRECT / ADMIN ACCESS
    # =========================================================

    @staticmethod
    @transaction.atomic
    def revoke_access(
        *,
        user,
        resource_type,
        resource,
        source=None,
        subscription=None,
    ):
        """
        Revoke direct user access to a resource.

        Used for:
            - Admin granted access
            - Individual access
            - Subscription-based access

        This method intentionally does NOT delete ResourceAccess.
        The record is retained for history/audit purposes.
        """

        if not user:
            raise ValueError(
                "User is required."
            )

        if not resource:
            raise ValueError(
                "Resource is required."
            )

        # -----------------------------------------------------
        # Validate resource type
        # -----------------------------------------------------

        if resource_type not in (
            AccessService.RESOURCE_COURSE,
            AccessService.RESOURCE_TRACK,
            AccessService.RESOURCE_EXAM,
        ):
            raise ValueError(
                f"Invalid resource type: {resource_type}"
            )

        # -----------------------------------------------------
        # Resource field
        # -----------------------------------------------------

        resource_fields = (
            AccessService._resource_filter(
                resource_type,
                resource,
            )
        )

        # -----------------------------------------------------
        # Find access records
        # -----------------------------------------------------

        filters = {
            "user": user,
            "resource_type": resource_type,
            **resource_fields,
        }

        # If a specific source was supplied, restrict
        # revocation to that source.
        if source is not None:
            filters["source"] = source

        # If a specific subscription was supplied,
        # restrict revocation to that subscription.
        if subscription is not None:
            filters["subscription"] = subscription

        access_qs = (
            ResourceAccess.objects
            .select_for_update()
            .filter(**filters)
        )

        # -----------------------------------------------------
        # Revoke
        # -----------------------------------------------------

        access_count = access_qs.update(
            is_active=False,
            revoked_at=timezone.now(),
        )

        return {
            "access_revoked": access_count > 0,
            "access_count": access_count,
        }
    







    # =========================================================
    # CHECK STUDENT ACCESS
    # =========================================================
        # =========================================================
    # CHECK STUDENT ACCESS
    # =========================================================

    @staticmethod
    def has_access(
        *,
        student,
        resource_type,
        resource,
    ):
        """
        Determine whether a student currently has access
        to a resource.

        Access can come from:

        1. Direct ResourceAccess
        2. Track access when the requested resource is an
           exam belonging to that track

        Track inheritance:

            Track ResourceAccess
                    ↓
              Exam belongs to Track
                    ↓
                Exam access
        """

        # =====================================================
        # BASIC VALIDATION
        # =====================================================

        if not student:
            return False

        if not resource:
            return False

        # =====================================================
        # VALID RESOURCE TYPE
        # =====================================================

        if resource_type not in (
            AccessService.RESOURCE_COURSE,
            AccessService.RESOURCE_TRACK,
            AccessService.RESOURCE_EXAM,
        ):
            return False

        # =====================================================
        # 1. DIRECT RESOURCE ACCESS
        # =====================================================

        resource_fields = (
            AccessService._resource_filter(
                resource_type,
                resource,
            )
        )

        access = (
            ResourceAccess.objects
            .select_related(
                "subscription",
                "assignment",
                "organization",
            )
            .filter(
                user=student,
                resource_type=resource_type,
                is_active=True,
                **resource_fields,
            )
            .order_by("-granted_at")
            .first()
        )

        if access:

            # -------------------------------------------------
            # ResourceAccess itself must be valid
            # -------------------------------------------------

            if access.is_valid():

                # ---------------------------------------------
                # Organization access
                # ---------------------------------------------

                if (
                    access.source
                    == ResourceAccess.SOURCE_ORGANIZATION
                ):

                    # Organization access requires a
                    # subscription.
                    if not access.subscription:
                        return False

                    # Subscription must still be valid.
                    if not access.subscription.is_valid():
                        return False

                    # Organization access requires assignment.
                    if not access.assignment:
                        return False

                    # Assignment must belong to student.
                    if (
                        access.assignment.student_id
                        != student.id
                    ):
                        return False

                    # Assignment and access organization must
                    # match.
                    if (
                        access.organization_id
                        != access.assignment.organization_id
                    ):
                        return False

                    assignment = access.assignment

                    # -----------------------------------------
                    # Verify assigned resource
                    # -----------------------------------------

                    if (
                        resource_type
                        == AccessService.RESOURCE_COURSE
                        and assignment.course_id
                        != resource.id
                    ):
                        return False

                    if (
                        resource_type
                        == AccessService.RESOURCE_TRACK
                        and assignment.track_id
                        != resource.id
                    ):
                        return False

                    if (
                        resource_type
                        == AccessService.RESOURCE_EXAM
                        and assignment.exam_id
                        != resource.id
                    ):
                        return False

                # ---------------------------------------------
                # Direct access is valid.
                # ---------------------------------------------

                else:

                    # If this is linked to a subscription,
                    # make sure that subscription is still valid.
                    if access.subscription:
                        if not access.subscription.is_valid():
                            return False

                return True

        # =====================================================
        # 2. TRACK → EXAM INHERITANCE
        # =====================================================
        #
        # If the requested resource is an Exam and that exam
        # belongs to a Track, valid Track access grants access
        # to the exam.
        #
        # We deliberately DO NOT create individual
        # ResourceAccess records for every exam.
        #
        # =====================================================

        if resource_type == AccessService.RESOURCE_EXAM:

            track = getattr(
                resource,
                "track",
                None,
            )

            # Exam is not associated with a track.
            if not track:
                return False

            # -------------------------------------------------
            # Find active Track access
            # -------------------------------------------------

            track_access = (
                ResourceAccess.objects
                .select_related(
                    "subscription",
                    "assignment",
                    "organization",
                )
                .filter(
                    user=student,
                    resource_type=AccessService.RESOURCE_TRACK,
                    track=track,
                    is_active=True,
                )
                .order_by("-granted_at")
                .first()
            )

            if not track_access:
                return False

            # -------------------------------------------------
            # Track ResourceAccess must be valid
            # -------------------------------------------------

            if not track_access.is_valid():
                return False

            # -------------------------------------------------
            # Track subscription must be valid if present
            # -------------------------------------------------

            if track_access.subscription:

                if not track_access.subscription.is_valid():
                    return False

            # -------------------------------------------------
            # Organization Track access
            # -------------------------------------------------

            if (
                track_access.source
                == ResourceAccess.SOURCE_ORGANIZATION
            ):

                # Organization access requires assignment.
                if not track_access.assignment:
                    return False

                assignment = track_access.assignment

                # Assignment must belong to this student.
                if (
                    assignment.student_id
                    != student.id
                ):
                    return False

                # Organization must match.
                if (
                    track_access.organization_id
                    != assignment.organization_id
                ):
                    return False

                # Assignment must actually point to this track.
                if assignment.track_id != track.id:
                    return False

            # -------------------------------------------------
            # Valid Track access grants Exam access
            # -------------------------------------------------

            return True

        # =====================================================
        # 3. NO ACCESS
        # =====================================================

        return False