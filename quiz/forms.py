from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import *


User = get_user_model()

class CustomerRegisterForm(forms.ModelForm):
    username = forms.CharField(widget=forms.TextInput(), required=True)
    password = forms.CharField(widget=forms.PasswordInput(), required=True)
    email = forms.CharField(widget=forms.EmailInput(), required=True)
    first_name = forms.CharField(widget=forms.TextInput(), required=True)
    last_name = forms.CharField(widget=forms.TextInput(), required=True)

    class Meta:
        model = Client
        fields = ('username', 'password', 'email', 'first_name', 'last_name', 'contact')

    def clean_username(self):
        uname = self.cleaned_data.get('username')
        if User.objects.filter(username=uname).exists():
            raise forms.ValidationError("Customer with this username already exists")
        return uname

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Customer with this email already exists")
        return email



# ==========================
# Registration Form
# ==========================
class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "your@email.com"})
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email


# ==========================
# Login Form (Username or Email)
# ==========================
class EmailOrUsernameLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "input", "placeholder": "Username or Email"}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "input", "placeholder": "Password"}
        )
    )

from django import forms
from ckeditor.widgets import CKEditorWidget
from .models import Question, Choice


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
            "text": CKEditorWidget(config_name="default"),
            "explanation": CKEditorWidget(config_name="default"),
        }


class ChoiceForm(forms.ModelForm):

    class Meta:
        model = Choice
        fields = ["text", "is_correct", "order"]

from django import forms
from quiz.models import Exam, ExamTrack

from django import forms
from quiz.models import Exam, ExamTrack


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

    def __init__(self, *args, **kwargs):

        organization = kwargs.pop("organization", None)

        super().__init__(*args, **kwargs)

        # 🔐 Restrict tracks to organization
        if organization:
            self.fields["track"].queryset = ExamTrack.objects.filter(
                organization=organization,
                is_active=True
            )

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
            "description": forms.Textarea(attrs={
                "rows": 4,
                "class": "textarea"
            })
        }



from django import forms
from quiz.models import Domain, Category


class DomainForm(forms.ModelForm):

    class Meta:
        model = Domain
        fields = ["name", "slug", "is_active"]


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