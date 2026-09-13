from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import models
from django.forms import BaseInlineFormSet, inlineformset_factory

from accounts.models.client import Client
from ckeditor.widgets import CKEditorWidget
from subscriptions.models import SubscriptionPlan
from organizations.models.organization import Organization

from .models import Category, Choice, Domain, Exam, ExamCategoryAllocation, ExamTrack, Question
from .search_widgets import SearchableModelMultipleChoiceWidget

User = get_user_model()


class CustomerRegisterForm(forms.ModelForm):
    username = forms.CharField(widget=forms.TextInput(), required=True)
    password = forms.CharField(widget=forms.PasswordInput(), required=True)
    email = forms.CharField(widget=forms.EmailInput(), required=True)
    first_name = forms.CharField(widget=forms.TextInput(), required=True)
    last_name = forms.CharField(widget=forms.TextInput(), required=True)

    class Meta:
        model = Client
        fields = ("username", "password", "email", "first_name", "last_name", "contact")

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Customer with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"placeholder": "your@email.com"}))

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email


class EmailOrUsernameLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "input", "placeholder": "Username or Email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input", "placeholder": "Password"}))


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["primary_category", "categories", "difficulty", "question_type", "text", "explanation"]
        widgets = {"categories": forms.CheckboxSelectMultiple(), "text": CKEditorWidget(config_name="default"), "explanation": CKEditorWidget(config_name="default")}

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        category_qs = Category.objects.filter(is_active=True).select_related("domain", "parent").order_by("domain__name", "parent__name", "name")
        if organization is not None:
            category_qs = category_qs.filter(models.Q(organization=organization) | models.Q(organization__isnull=True))
        self.fields["primary_category"].queryset = category_qs
        self.fields["categories"].queryset = category_qs
        self.fields["primary_category"].label = "Primary Category"
        self.fields["categories"].label = "Additional Categories"
        self.fields["categories"].required = False


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ["text", "is_correct", "order"]


class ExamForm(forms.ModelForm):
    """Manage reusable exam content; access is inherited from Course/Track."""

    class Meta:
        model = Exam
        fields = [
            "title", "organization", "categories",
            "question_count", "duration_seconds", "level", "passing_score",
            "is_published", "max_mock_attempts", "allow_review",
        ]
        widgets = {
            "categories": SearchableModelMultipleChoiceWidget(attrs={
                "data-autocomplete-scope": "categories",
                "data-search-placeholder": "Search categories...",
            }),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        category_qs = Category.objects.filter(is_active=True).select_related("domain", "parent").order_by("domain__name", "parent__name", "name")
        if organization is not None:
            category_qs = category_qs.filter(models.Q(organization=organization) | models.Q(organization__isnull=True))

        self.fields["organization"].queryset = Organization.objects.filter(
            models.Q(is_active=True) | models.Q(pk=self.instance.organization_id)
        ).order_by("name")
        self.fields["organization"].required = False
        self.fields["organization"].label = "Organization"
        self.fields["organization"].help_text = "Leave blank for a platform-wide exam."

        self.fields["categories"].queryset = category_qs
        self.fields["categories"].label = "Categories"
        self.fields["categories"].help_text = "Search by category name and select one or more categories. Only matching results are loaded."
        self.fields["categories"].required = False
        self.fields["question_count"].help_text = "Total number of questions allocated to each attempt."
        self.fields["duration_seconds"].help_text = "Maximum duration for one attempt, in seconds."
        self.fields["level"].help_text = "Positive difficulty/level value used by the exam catalog."
        self.fields["passing_score"].help_text = "Minimum percentage required to pass."
        self.fields["max_mock_attempts"].help_text = "Maximum mock attempts allowed; use 0 to disable mock attempts."
        self.fields["allow_review"].label = "Allow answer review"
        self.fields["allow_review"].help_text = "Allow students to review their answers before final submission."

    def clean(self):
        cleaned_data = super().clean()
        categories = cleaned_data.get("categories")
        organization = cleaned_data.get("organization")

        organization_id = organization.id if organization else None
        if categories:
            invalid_categories = [category for category in categories if category.organization_id not in (None, organization_id)]
            if invalid_categories:
                self.add_error("categories", "All categories must belong to the selected organization, or be global categories.")
            category_ids = [category.id for category in categories]
            if len(category_ids) != len(set(category_ids)):
                self.add_error("categories", "Duplicate categories are not allowed.")
        return cleaned_data


class ExamCategoryAllocationForm(forms.ModelForm):
    class Meta:
        model = ExamCategoryAllocation
        fields = ["category", "percentage", "fixed_count"]
        widgets = {
            "percentage": forms.NumberInput(attrs={"class": "input", "min": 1, "max": 100, "placeholder": "e.g. 20"}),
            "fixed_count": forms.NumberInput(attrs={"class": "input", "min": 1, "placeholder": "e.g. 10"}),
        }

    def __init__(self, *args, category_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if category_queryset is not None:
            self.fields["category"].queryset = category_queryset
        self.fields["category"].label = "Category"
        self.fields["percentage"].label = "Percentage"
        self.fields["fixed_count"].label = "Fixed Count"

    def clean(self):
        cleaned = super().clean()
        percentage = cleaned.get("percentage")
        fixed_count = cleaned.get("fixed_count")
        if percentage is not None and fixed_count is not None:
            raise forms.ValidationError("Use either percentage or fixed count, not both.")
        if percentage is None and fixed_count is None and not self.cleaned_data.get("DELETE"):
            raise forms.ValidationError("Enter a percentage or fixed question count.")
        return cleaned


class ExamCategoryAllocationFormSet(BaseInlineFormSet):
    def __init__(self, *args, category_queryset=None, **kwargs):
        self.category_queryset = category_queryset
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["category_queryset"] = self.category_queryset
        return kwargs

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        seen_categories = set()
        fixed_total = 0
        percentage_total = 0
        organization_id = getattr(self.instance, "organization_id", None)

        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue

            category = form.cleaned_data.get("category")
            if not category:
                continue

            if category.pk in seen_categories:
                form.add_error("category", "Each category can be allocated only once.")
            seen_categories.add(category.pk)

            if category.organization_id not in (None, organization_id):
                form.add_error("category", "Allocation category must belong to this exam's organization or be global.")

            fixed_total += form.cleaned_data.get("fixed_count") or 0
            percentage_total += form.cleaned_data.get("percentage") or 0

        question_count = getattr(self.instance, "question_count", None)
        if question_count and fixed_total > question_count:
            self.add_error(None, "Fixed category allocations cannot exceed the exam question count.")
        if percentage_total > 100:
            self.add_error(None, "Percentage category allocations cannot exceed 100%.")


ExamCategoryAllocationFormSet = inlineformset_factory(
    Exam,
    ExamCategoryAllocation,
    form=ExamCategoryAllocationForm,
    formset=ExamCategoryAllocationFormSet,
    extra=1,
    can_delete=True,
    fields=("category", "percentage", "fixed_count"),
)


class ExamTrackForm(forms.ModelForm):
    """Manage a sellable Track and the reusable exams it contains."""

    exams = forms.ModelMultipleChoiceField(queryset=Exam.objects.none(), required=False, widget=forms.SelectMultiple(attrs={"size": 10}), help_text="Select the reusable exams included in this track. Exams are not sold separately.")

    class Meta:
        model = ExamTrack
        fields = ["title", "slug", "description", "organization", "exams", "subscription_plans", "pricing_type", "monthly_price", "lifetime_price", "trial_days", "currency", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4, "class": "textarea"}), "subscription_plans": forms.SelectMultiple(attrs={"size": 8})}

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        exam_qs = Exam.objects.filter(is_published=True).order_by("title")
        if organization is not None:
            exam_qs = exam_qs.filter(models.Q(organization=organization) | models.Q(organization__isnull=True))
            self.fields["organization"].initial = organization
        self.fields["exams"].queryset = exam_qs
        self.fields["subscription_plans"].queryset = SubscriptionPlan.objects.filter(is_active=True, product_type=SubscriptionPlan.PRODUCT_TRACK, access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE).order_by("price", "name")
        self.fields["subscription_plans"].help_text = "Track product plans only. Buying a track grants this track and its included exams."
        if self.instance.pk:
            self.fields["exams"].initial = self.instance.track_exams.values_list("exam_id", flat=True)

    def clean(self):
        cleaned = super().clean()
        plans = cleaned.get("subscription_plans")
        pricing_type = cleaned.get("pricing_type")
        if plans and pricing_type != ExamTrack.PRICING_FREE:
            raise forms.ValidationError("Use Track Subscription Plans instead of legacy pricing.")
        return cleaned

    def save(self, commit=True):
        track = super().save(commit=commit)
        if commit:
            track.exams.set(self.cleaned_data.get("exams") or [])
            if track.subscription_scope != ExamTrack.TRACK:
                track.subscription_scope = ExamTrack.TRACK
                track.save(update_fields=["subscription_scope"])
        return track


class DomainForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ["name", "slug", "is_active"]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["domain", "name", "slug", "parent", "is_active"]
