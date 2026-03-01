from django.db import models
from django.conf import settings

class StaticPage(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_published = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    def __str__(self):
        return self.title


class Feedback(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    email = models.EmailField()
    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return self.email


from django.conf import settings
from django.db import models


class Testimonial(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    name = models.CharField(max_length=120)
    role = models.CharField(max_length=150, blank=True)

    message = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)

    # Correct relation to your model
    exam_track = models.ForeignKey(
        "quiz.ExamTrack",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    course = models.ForeignKey(
        "courses.Course",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    study_plan = models.ForeignKey(
        "quiz.StudyPlan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.rating}⭐)"