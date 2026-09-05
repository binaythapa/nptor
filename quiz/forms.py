from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
)

from accounts.models.client import Client
from django.db import models

from ckeditor.widgets import CKEditorWidget

from subscriptions.models import SubscriptionPlan

from .models import (
    Category,
    Choice,
    Domain,
    Exam,
    ExamTrack,
    Question,
)


User = get_user_model()


# ============================================================
# CUSTOMER REGISTRATION FORM
# ============================================================

class CustomerRegisterForm(forms.ModelForm):

    username = forms.CharField(
        widget=forms.TextInput(),
        required=True,
    )

    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True,
    )

    email = forms.CharField(
        widget=forms.EmailInput(),
        required=True,
    )

    first_name = forms.CharField(
        widget=forms.TextInput(),
        required=True,
    )

    last_name = forms.CharField(
        widget=forms.TextInput(),
        required=True,
    )

    class Meta:
        model = Client
        fields = (
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "contact",
        )

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


# ============================================================
# REGISTRATION FORM
# ============================================================

class RegistrationForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "your@email.com"}),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email


# ============================================================
# LOGIN FORM
# ============================================================

class EmailOrUsernameLoginForm(AuthenticationForm):

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Username or Email",
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "input",
                "placeholder": "Password",
            }
        )
    )


# ============================================================
# QUESTION FORM
# ============================================================

class QuestionForm(forms.ModelForm):

    class Meta:
        model = Question
        fields = [
            "primary_category",
            "categories",
            "difficulty",
            "question_type",
            "text",
            "explanation",
        ]
        widgets = {
            "categories": forms.CheckboxSelectMultiple(),
            "text": CKEditorWidget(config_name="default"),
            "explanation": CKEditorWidget(config_name="default"),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

        category_qs = (
            Category.objects
            .filter(is_active=True)
            .select_related("domain", "parent")
            .order_by("domain__name", "parent__name", "name")
        )

        if organization is not None:
            category_qs = category_qs.filter(
                models.Q(organization=organization)
                | models.Q(organization__isnull=True)
            )

        self.fields["primary_category"].queryset = category_qs
        self.fields["categories"].queryset = category_qs
        self.fields["primary_category"].label = "Primary Category"
        self.fields["categories"].label = "Additional Categories"
        self.fields["categories"].required = False


# ============================================================
# CHOICE FORM
# ============================================================

class ChoiceForm(forms.ModelForm):

    class Meta:
        model = Choice
        fields = [
            "text",
            "is_correct",
            "order",
        ]


# ============================================================
# EXAM FORM
# ============================================================

class ExamForm(forms.ModelForm):

    class Meta:
        model = Exam
        fields = [
            "title",
            "subscription_plans",
            "primary_category",
            "categories",
            "question_count",
            "duration_seconds",
            "level",
            "passing_score",
            "is_published",
            "max_mock_attempts",
            "allow_review",
        ]
        widgets = {
            "categories": forms.CheckboxSelectMultiple(),
            "subscription_plans": forms.SelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

        category_qs = (
            Category.objects
            .filter(is_active=True)
            .select_related("domain", "parent")
            .order_by("domain__name", "parent__name", "name")
        )

        if organization is not None:
            category_qs = category_qs.filter(
                models.Q(organization=organization)
                | models.Q(organization__isnull=True)
            )

        self.fields["subscription_plans"].queryset = (
            SubscriptionPlan.objects
            .filter(is_active=True)
            .order_by("price", "name")
        )
        self.fields["subscription_plans"].required = False
        self.fields["subscription_plans"].label = "Direct Access Plans"
        self.fields["subscription_plans"].help_text = (
            "Optional plans that grant direct access to this reusable exam. "
            "Track pricing remains independent."
        )

        self.fields["primary_category"].queryset = category_qs
        self.fields["categories"].queryset = category_qs
        self.fields["primary_category"].label = "Primary Category"
        self.fields["categories"].label = "Categories"
        self.fields["primary_category"].help_text = "Main category used to classify this exam."
        self.fields["categories"].help_text = "Select all categories covered by this exam."
        self.fields["primary_category"].required = False
        self.fields["categories"].required = False

    def clean(self):
        cleaned_data = super().clean()
        primary_category = cleaned_data.get("primary_category")
        categories = cleaned_data.get("categories")

        if primary_category:
            category_list = list(categories or [])
            if primary_category not in category_list:
                category_list.append(primary_category)
                cleaned_data["categories"] = category_list

        organization_id = self.instance.organization_id
        if organization_id:
            if primary_category and primary_category.organization_id not in (None, organization_id):
                self.add_error(
                    "primary_category",
                    "Primary category must belong to the same organization as the exam, or be a global category.",
                )

            if categories:
                invalid_categories = [
                    category
                    for category in categories
                    if category.organization_id not in (None, organization_id)
                ]
                if invalid_categories:
                    self.add_error(
                        "categories",
                        "All categories must belong to the same organization as the exam, or be global categories.",
                    )

        if categories:
            category_ids = [category.id for category in categories]
            if len(category_ids) != len(set(category_ids)):
                self.add_error("categories", "Duplicate categories are not allowed.")

        return cleaned_data


# ============================================================
# EXAM TRACK FORM
# ============================================================

class ExamTrackForm(forms.ModelForm):

    class Meta:
        model = ExamTrack
        fields = [
            "title",
            "slug",
            "description",
            "pricing_type",
            "monthly_price",
            "lifetime_price",
            "trial_days",
            "currency",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "textarea",
                }
            )
        }


# ============================================================
# DOMAIN FORM
# ============================================================

class DomainForm(forms.ModelForm):

    class Meta:
        model = Domain
        fields = [
            "name",
            "slug",
            "is_active",
        ]


# ============================================================
# CATEGORY FORM
# ============================================================

class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category
        fields = [
            "domain",
            "name",
            "slug",
            "parent",
            "is_active",
        ]
