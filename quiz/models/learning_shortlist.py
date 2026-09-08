from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class LearningShortlist(models.Model):
    """A user's saved learning resource, similar to a watchlist."""

    RESOURCE_COURSE = "course"
    RESOURCE_TRACK = "track"
    RESOURCE_EXAM = "exam"

    RESOURCE_TYPES = (
        (RESOURCE_COURSE, "Course"),
        (RESOURCE_TRACK, "Exam Track"),
        (RESOURCE_EXAM, "Exam"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="learning_shortlist",
    )
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    course = models.ForeignKey(
        "courses.Course",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="learning_shortlists",
    )
    track = models.ForeignKey(
        "quiz.ExamTrack",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="learning_shortlists",
    )
    exam = models.ForeignKey(
        "quiz.Exam",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="learning_shortlists",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def clean(self):
        fields = {
            self.RESOURCE_COURSE: self.course,
            self.RESOURCE_TRACK: self.track,
            self.RESOURCE_EXAM: self.exam,
        }
        if self.resource_type not in fields:
            raise ValidationError({"resource_type": "Unsupported resource type."})
        selected = [resource for resource in fields.values() if resource is not None]
        if len(selected) != 1 or fields[self.resource_type] is None:
            raise ValidationError(
                "Shortlist entry must contain exactly one resource matching resource_type."
            )

    def save(self, *args, **kwargs):
        """Persist safely on databases without conditional unique indexes.

        Locking the user's row serializes shortlist writes for that user, making
        the uniqueness check safe under concurrent requests on MySQL.
        """
        self.full_clean()

        with transaction.atomic():
            user = type(self.user).objects.select_for_update().get(pk=self.user_id)
            lookup = {
                "user_id": self.user_id,
                "resource_type": self.resource_type,
                **self.resource_lookup(self.resource_type, self.resource()),
            }
            duplicate = type(self).objects.filter(**lookup).exclude(pk=self.pk).exists()
            if duplicate:
                raise ValidationError(
                    "This resource is already in the user's shortlist."
                )
            return super().save(*args, **kwargs)

    @classmethod
    def resource_lookup(cls, resource_type, resource):
        fields = {
            cls.RESOURCE_COURSE: "course",
            cls.RESOURCE_TRACK: "track",
            cls.RESOURCE_EXAM: "exam",
        }
        field = fields.get(resource_type)
        if field is None:
            raise ValueError("Unsupported resource type.")
        return {field: resource}

    @classmethod
    def for_resource(cls, *, user, resource_type, resource):
        with transaction.atomic():
            cls.objects.select_for_update().filter(user=user).first()
            item, created = cls.objects.get_or_create(
                user=user,
                resource_type=resource_type,
                defaults=cls.resource_lookup(resource_type, resource),
            )
        return item, created

    @classmethod
    def remove_for_resource(cls, *, user, resource_type, resource):
        deleted, _ = cls.objects.filter(
            user=user,
            resource_type=resource_type,
            **cls.resource_lookup(resource_type, resource),
        ).delete()
        return deleted > 0

    def resource(self):
        return self.course or self.track or self.exam

    def __str__(self):
        return f"{self.user} → {self.resource_type} → {self.resource()}"
