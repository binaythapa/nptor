from django.db import models
from django.db.models import Q


class QuestionQuerySet(models.QuerySet):

    def active(self):
        return self.filter(
            is_active=True,
            is_deleted=False
        )

    def filter(self, *args, **kwargs):
        """
        Keep legacy category query syntax working while questions use
        primary_category plus the multi-category ``categories`` relation.

        Existing callers still use ``category__domain`` and
        ``category_id__in``. Translate those predicates to the canonical
        fields so old practice/admin paths do not fail with FieldError and
        questions assigned through either category relation remain visible.
        """
        legacy_domain = kwargs.pop("category__domain", None)
        legacy_category_ids = kwargs.pop("category_id__in", None)

        if legacy_domain is not None:
            args = tuple(args) + (
                Q(primary_category__domain=legacy_domain)
                | Q(categories__domain=legacy_domain),
            )

        if legacy_category_ids is not None:
            args = tuple(args) + (
                Q(primary_category_id__in=legacy_category_ids)
                | Q(categories__id__in=legacy_category_ids),
            )

        queryset = super().filter(*args, **kwargs)

        if legacy_domain is not None or legacy_category_ids is not None:
            queryset = queryset.distinct()

        return queryset
