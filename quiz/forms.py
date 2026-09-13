from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import models

from accounts.models.client import Client
from ckeditor.widgets import CKEditorWidget
from subscriptions.models import SubscriptionPlan
from organizations.models.organization import Organization

from .models import Category, Choice, Domain, Exam, ExamTrack, Question
from .search_widgets import SearchableModelChoiceWidget, SearchableModelMultipleChoiceWidget

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
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Customer with this email already exists.")
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
            "title", "organization", "primary_category", "categories",
            "question_count", "duration_seconds", "level", "passing_score",
            "is_published", "max_mock_attempts", "allow_review",
        ]
        widgets = {
            "primary_category": SearchableModelChoiceWidget(attrs={
                "data-autocomplete-scope": "categories",
                "data-search-placeholder": "Search primary category...",
            }),
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

        self.fields["primary_category"].queryset = category_qs
        self.fields["categories"].queryset = category_qs
        self.fields["primary_category"].label = "Primary Category"
        self.fields["categories"].label = "Categories"
        self.fields["primary_category"].help_text = "Main category used to classify this exam."
        self.fields["categories"].help_text = "Search by category name and select one or more categories. Only matching results are loaded."
        self.fields["primary_category"].required = False
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
        primary_category = cleaned_data.get("primary_category")
        categories = cleaned_data.get("categories")
        organization = cleaned_data.get("organization")

        if primary_category:
            category_list = list(categories or [])
            if primary_category not in category_list:
                category_list.append(primary_category)
                cleaned_data["categories"] = category_list

        organization_id = organization.id if organization else None
        if primary_category and primary_category.organization_id not in (None, organization_id):
            self.add_error("primary_category", "Primary category must belong to the selected organization, or be a global category.")
        if categories:
            invalid_categories = [category for category in categories if category.organization_id not in (None, organization_id)]
            if invalid_categories:
                self.add_error("categories", "All categories must belong to the selected organization, or be global categories.")
            category_ids = [category.id for category in categories]
            if len(category_ids) != len(set(category_ids)):
                self.add_error("categories", "Duplicate categories are not allowed.")
        return cleaned_data


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
