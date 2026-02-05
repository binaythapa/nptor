from django.db import models
from django.conf import settings

class Notification(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()

    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="notifications",
        help_text="Empty = broadcast to all users"
    )

    read_by = models.JSONField(
        default=dict,
        blank=True,
        help_text="Map of user_id -> read status"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_as_read(self, user):
        self.read_by[str(user.id)] = True
        self.save(update_fields=["read_by"])

    def is_unread_for(self, user):
        return not self.read_by.get(str(user.id), False)

    def __str__(self):
        return self.title
