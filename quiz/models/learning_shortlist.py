from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


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
        "auth.User",
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
        constraints = [
            models.UniqueConstraint(
                fields=["user", "resource_type", "course"],
                condition=Q(resource_type="course"),
                name="uniq_shortlist_user_course",
            ),
            models.UniqueConstraint(
                fields=["user", "resource_type", "track"],
                condition=Q(resource_type="track"),
                name="uniq_shortlist_user_track",
            ),
            models.UniqueConstraint(
                fields=["user", "resource_type", "exam"],
                condition=Q(resource_type="exam"),
                name="uniq_shortlist_user_exam",
            ),
        ]

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

    @classmethod
    def for_resource(cls, *, user, resource_type, resource):
        if resource_type == cls.RESOURCE_COURSE:
            lookup = {"course": resource}
        elif resource_type == cls.RESOURCE_TRACK:
            lookup = {"track": resource}
        elif resource_type == cls.RESOURCE_EXAM:
            lookup = {"exam": resource}
        else:
            raise ValueError("Unsupported resource type.")

        item, created = cls.objects.get_or_create(
            user=user,
            resource_type=resource_type,
            defaults=lookup,
        )
        return type("ShortlistResult", (), {"item": item, "created": created})

    @classmethod
    def remove_for_resource(cls, *, user, resource_type, resource):
        if resource_type == cls.RESOURCE_COURSE:
            lookup = {"course": resource}
        elif resource_type == cls.RESOURCE_TRACK:
            lookup = {"track": resource}
        elif resource_type == cls.RESOURCE_EXAM:
            lookup = {"exam": resource}
        else:
            raise ValueError("Unsupported resource type.")

        deleted, _ = cls.objects.filter(
            user=user,
            resource_type=resource_type,
            **lookup,
        ).delete()
        return deleted > 0

    def resource(self):
        return self.course or self.track or self.exam

    def __str__(self):
        return f"{self.user} → {self.resource_type} → {self.resource()}"
