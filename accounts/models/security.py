from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class AccountLock(models.Model):
    """
    Tracks failed authentication attempts
    and temporarily locks accounts.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_lock"
    )

    failed_attempts = models.PositiveIntegerField(default=0)

    locked_until = models.DateTimeField(
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(auto_now=True)

    # ============================
    # CONFIG (SAFE DEFAULTS)
    # ============================
    MAX_ATTEMPTS = 5
    LOCK_DURATION = timedelta(minutes=15)

    def is_locked(self):
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def register_failure(self):
        self.failed_attempts += 1

        if self.failed_attempts >= self.MAX_ATTEMPTS:
            self.locked_until = timezone.now() + self.LOCK_DURATION

        self.save(update_fields=["failed_attempts", "locked_until", "updated_at"])

    def reset(self):
        self.failed_attempts = 0
        self.locked_until = None
        self.save(update_fields=["failed_attempts", "locked_until", "updated_at"])

    def __str__(self):
        return f"Lock({self.user})"
