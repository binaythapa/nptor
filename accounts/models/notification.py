from django.db import models
from django.conf import settings


class Notification(models.Model):
    PRIORITY_INFO = "info"
    PRIORITY_SUCCESS = "success"
    PRIORITY_WARNING = "warning"
    PRIORITY_CRITICAL = "critical"
    PRIORITY_CHOICES = (
        (PRIORITY_INFO, "Info"),
        (PRIORITY_SUCCESS, "Success"),
        (PRIORITY_WARNING, "Warning"),
        (PRIORITY_CRITICAL, "Critical"),
    )

    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default="system")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_INFO)
    target_url = models.CharField(max_length=500, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    dedupe_key = models.CharField(max_length=200, blank=True, null=True, unique=True)
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="notifications", help_text="Empty = broadcast to all users")
    read_by = models.JSONField(default=dict, blank=True, help_text="Map of user_id -> read status")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["notification_type", "created_at"], name="notification_type_date_idx")]

    def mark_as_read(self, user):
        read_by = dict(self.read_by or {})
        read_by[str(user.id)] = True
        self.read_by = read_by
        self.save(update_fields=["read_by"])

    def is_unread_for(self, user):
        return not (self.read_by or {}).get(str(user.id), False)

    def is_visible_to(self, user):
        return not self.recipients.exists() or self.recipients.filter(pk=user.pk).exists()

    def __str__(self):
        return self.title
