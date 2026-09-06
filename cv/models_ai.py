from django.conf import settings
from django.db import models

from cv.models_cv import CV
from cv.models_version import CVVersion


class AIConversation(models.Model):
    PURPOSE_INTERVIEW = "interview"
    PURPOSE_WRITER = "writer"
    PURPOSE_REVIEW = "review"
    PURPOSE_JOB_MATCH = "job_match"
    PURPOSE_CHOICES = (
        (PURPOSE_INTERVIEW, "Career interview"),
        (PURPOSE_WRITER, "CV writer"),
        (PURPOSE_REVIEW, "CV review"),
        (PURPOSE_JOB_MATCH, "Job match"),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_ai_conversations")
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, null=True, blank=True, related_name="ai_conversations")
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES, default=PURPOSE_INTERVIEW)
    provider = models.CharField(max_length=60, blank=True)
    model = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [models.Index(fields=["owner", "purpose"], name="cv_ai_conv_owner_idx")]

    def __str__(self):
        return f"AI {self.purpose}: {self.owner.get_username()}"


class AIMessage(models.Model):
    ROLE_SYSTEM = "system"
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_CHOICES = (
        (ROLE_SYSTEM, "System"),
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
    )

    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    provider_response_id = models.CharField(max_length=150, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class AIExtraction(models.Model):
    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name="extractions")
    source_message = models.ForeignKey(AIMessage, on_delete=models.SET_NULL, null=True, blank=True, related_name="extractions")
    section = models.CharField(max_length=60)
    field_name = models.CharField(max_length=120)
    proposed_value = models.JSONField(default=dict, blank=True)
    confirmed = models.BooleanField(default=False, db_index=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="confirmed_cv_ai_extractions")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["conversation", "confirmed"], name="cv_ai_extract_idx")]


class ATSAnalysis(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_ai_ats_analyses")
    cv_version = models.ForeignKey(CVVersion, on_delete=models.CASCADE, null=True, blank=True, related_name="ats_analyses")
    conversation = models.ForeignKey(AIConversation, on_delete=models.SET_NULL, null=True, blank=True, related_name="ats_analyses")
    job_description = models.TextField(blank=True)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    result = models.JSONField(default=dict, blank=True)
    provider = models.CharField(max_length=60, blank=True)
    model = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["owner", "created_at"], name="cv_ai_ats_owner_idx")]


class AISuggestion(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
    )

    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name="suggestions")
    section = models.CharField(max_length=60)
    field_name = models.CharField(max_length=120)
    kind = models.CharField(max_length=40, default="improvement")
    title = models.CharField(max_length=255)
    reason = models.TextField(blank=True)
    current_value = models.JSONField(default=dict, blank=True)
    proposed_value = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    accepted = models.BooleanField(default=False)
    acted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["conversation", "status"], name="cv_ai_sugg_status_idx")]
