from django import forms
from django.db import models

from quiz.models import Exam, ExamTrack
from subscriptions.models import SubscriptionPlan


class TrackSubscriptionPlanMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, plan):
        interval = plan.get_billing_interval_label()
        return f"{plan.name} — {plan.currency} {plan.price} / {interval}"


class TrackCommerceForm(forms.ModelForm):
    """Global Track form using Track Subscription Plans as the only pricing model."""

    exams = forms.ModelMultipleChoiceField(
        queryset=Exam.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10}),
        help_text="Select the reusable exams included in this Track. Exams are not sold separately.",
    )

    subscription_plans = TrackSubscriptionPlanMultipleChoiceField(
        queryset=SubscriptionPlan.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 8}),
        help_text="Select the Track offers customers can purchase. Each offer defines its own price and billing interval.",
    )

    class Meta:
        model = ExamTrack
        fields = [
            "title",
            "slug",
            "description",
            "organization",
            "exams",
            "subscription_plans",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "class": "textarea"}),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

        exam_qs = Exam.objects.filter(is_published=True).order_by("title")
        if organization is not None:
            exam_qs = exam_qs.filter(
                models.Q(organization=organization) | models.Q(organization__isnull=True)
            )
            self.fields["organization"].initial = organization

        self.fields["exams"].queryset = exam_qs
        self.fields["subscription_plans"].queryset = (
            SubscriptionPlan.objects
            .filter(
                is_active=True,
                product_type=SubscriptionPlan.PRODUCT_TRACK,
                access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            )
            .order_by("price", "name")
        )

        if self.instance.pk:
            self.fields["exams"].initial = self.instance.track_exams.values_list("exam_id", flat=True)
            self.fields["subscription_plans"].initial = self.instance.subscription_plans.all()

    def clean(self):
        cleaned = super().clean()
        plans = cleaned.get("subscription_plans") or []
        invalid = [
            plan for plan in plans
            if plan.product_type != SubscriptionPlan.PRODUCT_TRACK
            or plan.access_mode != SubscriptionPlan.ACCESS_SINGLE_RESOURCE
        ]
        if invalid:
            self.add_error("subscription_plans", "Only single-resource Track plans can be attached to a Track.")
        return cleaned

    def save(self, commit=True):
        track = super().save(commit=commit)
        if commit:
            track.exams.set(self.cleaned_data.get("exams") or [])
            track.subscription_plans.set(self.cleaned_data.get("subscription_plans") or [])
            if track.subscription_scope != ExamTrack.TRACK:
                track.subscription_scope = ExamTrack.TRACK
                track.save(update_fields=["subscription_scope"])
        return track
