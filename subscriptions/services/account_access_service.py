from django.core.exceptions import ValidationError
from django.db import transaction

from subscriptions.models import AccountSubscriptionSelection, Subscription


class AccountAccessService:
    """Resolve and manage Course/Track access supplied by Account plans."""

    @staticmethod
    def _valid_account_subscriptions(user):
        return (
            Subscription.objects
            .select_related("plan")
            .filter(
                user=user,
                status=Subscription.STATUS_ACTIVE,
                plan__product_type=Subscription.plan.field.related_model.PRODUCT_ACCOUNT,
                plan__is_active=True,
            )
        )

    @staticmethod
    def has_course_access(user, course):
        if not user or not course:
            return False
        for subscription in AccountAccessService._valid_account_subscriptions(user):
            if not subscription.is_valid():
                continue
            plan = subscription.plan
            if plan.is_all_access():
                return True
            if plan.is_limited_account_plan() and AccountSubscriptionSelection.objects.filter(
                subscription=subscription, course=course
            ).exists():
                return True
        return False

    @staticmethod
    def has_track_access(user, track):
        if not user or not track:
            return False
        for subscription in AccountAccessService._valid_account_subscriptions(user):
            if not subscription.is_valid():
                continue
            plan = subscription.plan
            if plan.is_all_access():
                return True
            if plan.is_limited_account_plan() and AccountSubscriptionSelection.objects.filter(
                subscription=subscription, track=track
            ).exists():
                return True
        return False

    @staticmethod
    def _get_subscription_for_update(subscription, user):
        locked = (
            Subscription.objects
            .select_for_update()
            .select_related("plan")
            .filter(pk=subscription.pk, user=user)
            .first()
        )
        if not locked or not locked.is_valid():
            raise ValidationError("Account subscription is not currently valid.")
        if not locked.plan.is_account_plan():
            raise ValidationError("The subscription plan is not an Account plan.")
        if not locked.plan.is_limited_account_plan():
            raise ValidationError("Resource selection is only available for limited Account plans.")
        return locked

    @staticmethod
    @transaction.atomic
    def select_course(*, subscription, course, user=None):
        user = user or subscription.user
        if not user or subscription.user_id != user.id:
            raise ValidationError("Account subscription does not belong to this user.")
        locked = AccountAccessService._get_subscription_for_update(subscription, user)
        if AccountSubscriptionSelection.objects.filter(subscription=locked, course=course).exists():
            return AccountSubscriptionSelection.objects.get(subscription=locked, course=course), False
        quota = locked.plan.max_courses or 0
        used = AccountSubscriptionSelection.objects.filter(subscription=locked, course__isnull=False).count()
        if used >= quota:
            raise ValidationError("The Course selection quota has been reached.")
        selection = AccountSubscriptionSelection(subscription=locked, course=course)
        selection.full_clean()
        selection.save()
        return selection, True

    @staticmethod
    @transaction.atomic
    def select_track(*, subscription, track, user=None):
        user = user or subscription.user
        if not user or subscription.user_id != user.id:
            raise ValidationError("Account subscription does not belong to this user.")
        locked = AccountAccessService._get_subscription_for_update(subscription, user)
        if AccountSubscriptionSelection.objects.filter(subscription=locked, track=track).exists():
            return AccountSubscriptionSelection.objects.get(subscription=locked, track=track), False
        quota = locked.plan.max_tracks or 0
        used = AccountSubscriptionSelection.objects.filter(subscription=locked, track__isnull=False).count()
        if used >= quota:
            raise ValidationError("The Track selection quota has been reached.")
        selection = AccountSubscriptionSelection(subscription=locked, track=track)
        selection.full_clean()
        selection.save()
        return selection, True

    @staticmethod
    def selections(subscription):
        return AccountSubscriptionSelection.objects.filter(subscription=subscription).select_related("course", "track")
