from django.db import models
from quiz.models import Category,SubscriptionPlan
from organizations.models.organization import Organization
from django.conf import settings
#from .plan import SubscriptionPlan
from django.utils.text import slugify
import uuid




# =====================================================
# COURSE
# =====================================================

class Course(models.Model):
    title = models.CharField(max_length=255)    
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()



    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses"
    )

    thumbnail = models.ImageField(
        upload_to="courses/",
        null=True,
        blank=True
    )

    level = models.CharField(
        max_length=20,
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ]
    )

    subscription_plans = models.ManyToManyField(
        SubscriptionPlan,
        blank=True,
        related_name="course_access_courses"
    )

    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # 🔥 ADD THIS
    is_deleted = models.BooleanField(default=False)



    ###########ORG############
    OWNER_CHOICES = (
        ("platform", "Platform"),
        ("organization", "Organization"),
    )

    owner_type = models.CharField(
        max_length=20,
        choices=OWNER_CHOICES,
        default="platform"
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    is_public = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="courses_created"
        )


    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
    

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            unique_slug = base_slug
            counter = 1

            while Course.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = unique_slug

        super().save(*args, **kwargs)
