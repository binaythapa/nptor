from django.conf import settings
from django.db import models


class CareerProfile(models.Model):
    """Reusable master career profile owned by one NPTOR account."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="career_profile")
    professional_title = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    is_confirmed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id"]

    def __str__(self):
        return f"Career profile: {self.user.get_username()}"


class CareerProfileChild(models.Model):
    profile = models.ForeignKey(CareerProfile, on_delete=models.CASCADE)
    sort_order = models.PositiveIntegerField(default=0)
    is_confirmed = models.BooleanField(default=True)
    source = models.CharField(max_length=40, default="user", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["sort_order", "id"]


class CareerExperience(CareerProfileChild):
    profile = models.ForeignKey(CareerProfile, on_delete=models.CASCADE, related_name="careerexperience_records")
    job_title = models.CharField(max_length=255)
    employer = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def __str__(self): return f"{self.job_title} - {self.employer}"


class CareerEducation(CareerProfileChild):
    profile = models.ForeignKey(CareerProfile, on_delete=models.CASCADE, related_name="careereducation_records")
    institution = models.CharField(max_length=255)
    qualification = models.CharField(max_length=255)
    field_of_study = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self): return f"{self.qualification} - {self.institution}"


class CareerProject(CareerProfileChild):
    profile = models.ForeignKey(CareerProfile, on_delete=models.CASCADE, related_name="careerproject_records")
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    technologies = models.CharField(max_length=1000, blank=True)

    def __str__(self): return self.name


class CareerSkill(CareerProfileChild):
    profile = models.ForeignKey(CareerProfile, on_delete=models.CASCADE, related_name="careerskill_records")
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    proficiency = models.CharField(max_length=100, blank=True)

    def __str__(self): return self.name


class CareerAchievement(CareerProfileChild):
    profile = models.ForeignKey(CareerProfile, on_delete=models.CASCADE, related_name="careerachievement_records")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    achieved_on = models.DateField(null=True, blank=True)

    def __str__(self): return self.title


class CareerCertification(CareerProfileChild):
    profile = models.ForeignKey(CareerProfile, on_delete=models.CASCADE, related_name="careercertification_records")
    name = models.CharField(max_length=255)
    issuer = models.CharField(max_length=255, blank=True)
    credential_id = models.CharField(max_length=255, blank=True)
    credential_url = models.URLField(blank=True)
    issued_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)

    def __str__(self): return self.name


# Re-export split CV domain models so existing cv.models imports remain compatible.
# Keep these imports below CareerProfile because the split modules reference it.
from cv.models_cv import CV  # noqa: E402,F401
from cv.models_template import CVTemplate  # noqa: E402,F401
from cv.models_version import CVVersion  # noqa: E402,F401
from cv.models_document import DocumentArtifact  # noqa: E402,F401
from cv.models_import import CVImport, ImportedField  # noqa: E402,F401
