from django.conf import settings
from django.db import models


class Notification(models.Model):
    title = models.CharField(
        max_length=200
    )

    message = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        help_text=(
            "Leave empty to target all users "
            "(broadcast)."
        ),
    )

    is_read_by = models.JSONField(
        default=dict,
        blank=True,
        help_text="Map user_id -> true",
    )

    def mark_read(self, user):
        data = self.is_read_by or {}

        data[str(user.id)] = True

        self.is_read_by = data

        self.save(
            update_fields=["is_read_by"]
        )

    def unread_for(self, user):
        return not self.is_read_by.get(
            str(user.id),
            False,
        )

    def __str__(self):
        return self.title