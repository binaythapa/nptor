from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
)

from accounts.models.client import Client

from ckeditor.widgets import CKEditorWidget

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

        if User.objects.filter(
            username=username
        ).exists():
            raise forms.ValidationError(
                "Customer with this username already exists."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if User.objects.filter(
            email=email
        ).exists():
            raise forms.ValidationError(
                "Customer with this email already exists."
            )

        return email


# ============================================================
# REGISTRATION FORM
# ============================================================

class RegistrationForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "placeholder": "your@email.com",
            }
        ),
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

        if User.objects.filter(
            email__iexact=email
        ).exists():
            raise forms.ValidationError(
                "This email is already in use."
            )

        return email


# ============================================================
# LOGIN FORM
# Username OR Email + Password
# ============================================================

class EmailOrUsernameLoginForm(
    AuthenticationForm
):

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
            "category",
            "difficulty",
            "question_type",
            "text",
            "explanation",
        ]

        widgets = {
            "text": CKEditorWidget(
                config_name="default"
            ),
            "explanation": CKEditorWidget(
                config_name="default"
            ),
        }


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
            "track",
            "category",
            "categories",
            "question_count",
            "duration_seconds",
            "level",
            "passing_score",
            "prerequisite_exams",
            "is_free",
            "price",
            "currency",
            "is_published",
            "max_mock_attempts",
            "allow_review",
        ]

        widgets = {
            "categories": forms.CheckboxSelectMultiple(),
            "prerequisite_exams": forms.SelectMultiple(),
        }

    def __init__(
        self,
        *args,
        **kwargs
    ):
        organization = kwargs.pop(
            "organization",
            None,
        )

        super().__init__(
            *args,
            **kwargs,
        )

        # Restrict tracks to organization
        if organization:
            self.fields[
                "track"
            ].queryset = ExamTrack.objects.filter(
                organization=organization,
                is_active=True,
            )


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