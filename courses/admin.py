from django.contrib import admin
from django.utils.html import format_html
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import admin
from django.utils import timezone
from django.db import transaction
from django.db.models import F

from courses.models import *

#from .models import *

# =========================
# INLINE CONFIGS
# =========================

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = (
        "title",
        "lesson_type",
        "order",
        "exam",
        "practice_category",
        "video_url",
    )
    ordering = ("order",)


class CourseSectionInline(admin.StackedInline):
    model = CourseSection
    extra = 1
    show_change_link = True
    fields = ("title", "order")
    ordering = ("order",)


# =========================
# MAIN ADMINS
# =========================
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "organization",
        "level",
        "is_published",
       
        "created_at",
    )

    list_filter = (
        "organization",
        "is_published",
        
        "level",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "organization__name",
    )

    prepopulated_fields = {"slug": ("title",)}

    filter_horizontal = ("subscription_plans",)

    inlines = (CourseSectionInline,)

    fieldsets = (

        ("Basic Info", {
            "fields": (
                "title",
                "slug",
                "description",
                "category",
                "thumbnail",
            )
        }),

        ("Ownership", {
            "fields": (
                "organization",
            ),
            "description": (
                "Leave empty for public/platform courses. "
                "Select an organization for org-owned courses."
            )
        }),

        ("Level & Access", {
            "fields": (
                "level",
                "subscription_plans",
                "is_published",
                
            )
        }),

        ("Meta", {
            "fields": ("created_at",),
        }),
    )

    readonly_fields = ("created_at",)


@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "course",
        "order",
      
        "created_at",   # optional if you added it
    )

    list_filter = (
        "course",
        
    )

    search_fields = ("title",)

    ordering = ("course", "order")

    inlines = (LessonInline,)

    readonly_fields = ("created_at", "updated_at")  # optional
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):

    # =========================
    # LIST VIEW
    # =========================
    list_display = (
        "title",
        "section",
        "lesson_type",
        "order",
        "linked_resource",
        "practice_difficulty",
    )

    list_filter = (
        "lesson_type",
        "section__course",
        "practice_difficulty",
    )

    search_fields = ("title",)
    ordering = ("section", "order")

    # =========================
    # EDIT FORM STRUCTURE
    # =========================
    fieldsets = (
        ("📘 Lesson Info", {
            "fields": (
                "section",
                "title",
                "lesson_type",
                "order",
            )
        }),

        ("🎥 Video Content", {
            "fields": ("video_url",),
            "classes": ("collapse",),
        }),

        ("📝 Article Content", {
            "fields": ("article_content", "article_preview"),
            "description": (
                "You can paste HTML here. "
                "Images can be placed anywhere using "
                "<code>&lt;img&gt;</code> with CSS classes "
                "(align-left, align-center, img-medium, etc.)"
            ),
        }),

        ("🧪 Practice Configuration", {
            "fields": (
                "practice_domain",
                "practice_category",
                "practice_difficulty",
                "practice_threshold",
                "practice_lock_filters",
                "practice_require_correct",
                "practice_min_accuracy",
            ),
            "classes": ("collapse",),
        }),

        ("🧠 Quiz Configuration", {
            "fields": (
                "exam",
                "quiz_completion_mode",
                "quiz_min_score",
                "quiz_allow_mock",
                "quiz_max_attempts",
            ),
            "classes": ("collapse",),
        }),
    )

    readonly_fields = ("article_preview",)

    class Media:
        css = {
            "all": ("css/lesson.css",)
        }

    # =========================
    # RESOURCE LABEL
    # =========================
    def linked_resource(self, obj):
        if obj.lesson_type == "quiz" and obj.exam:
            return f"Quiz: {obj.exam.title}"
        if obj.lesson_type == "practice" and obj.practice_category:
            return f"Practice: {obj.practice_category.name}"
        if obj.lesson_type == "video":
            return "Video"
        if obj.lesson_type == "article":
            return "Article"
        return "—"

    linked_resource.short_description = "Resource"

    # =========================
    # LIVE ARTICLE PREVIEW
    # =========================
    def article_preview(self, obj):
        if not obj.article_content:
            return "— No content yet —"

        return format_html(
            '<div class="lesson-content" '
            'style="max-height:400px; overflow:auto; '
            'border:1px solid #e5e7eb; padding:16px; '
            'background:#f9fafb;">{}</div>',
            mark_safe(obj.article_content),
        )

    article_preview.short_description = "📖 Article Preview"


    # -------------------------------------------------
    # Auto Reorder After Single Delete
    # -------------------------------------------------
    def delete_model(self, request, obj):
        with transaction.atomic():
            section = obj.section
            deleted_order = obj.order

            super().delete_model(request, obj)

            Lesson.objects.filter(
                section=section,
                order__gt=deleted_order
            ).update(order=F("order") - 1)

    # -------------------------------------------------
    # Auto Reorder After Bulk Delete
    # -------------------------------------------------
    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            # Group deletions by section
            sections = {}

            for lesson in queryset:
                sections.setdefault(lesson.section_id, []).append(lesson.order)

            super().delete_queryset(request, queryset)

            # Reorder each affected section
            for section_id in sections.keys():
                lessons = (
                    Lesson.objects
                    .filter(section_id=section_id)
                    .order_by("order")
                )

                for index, lesson in enumerate(lessons, start=1):
                    if lesson.order != index:
                        lesson.order = index
                        lesson.save(update_fields=["order"])



# =========================
# READ-ONLY / SUPPORT ADMINS
# =========================

@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "course",
        "is_active",
        "enrolled_at",
    )
    list_filter = ("is_active", "course")
    search_fields = ("user__username", "course__title")
    readonly_fields = ("enrolled_at",)


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "lesson",
        "completed",
        "completed_at",
    )
    list_filter = ("completed", "lesson__section__course")
    search_fields = ("user__username", "lesson__title")
    readonly_fields = ("completed_at",)





@admin.register(CourseSubscription)
class CourseSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "course",
        "is_active",
        "expires_at",
        "payment_required",
        "amount",
        "currency",
        "subscribed_by_admin",
        "subscribed_at",
    )

    list_filter = (
        "is_active",
        "payment_required",
        "subscribed_by_admin",
        "currency",
        "course",
    )

    search_fields = (
        "user__username",
        "user__email",
        "course__title",
        "payment_id",
    )

    autocomplete_fields = ("user", "course")

    ordering = ("-subscribed_at",)

    readonly_fields = (
        "subscribed_at",
    )

    fieldsets = (
        ("📘 Subscription Info", {
            "fields": (
                "user",
                "course",
                "is_active",
            )
        }),

        ("⏳ Validity", {
            "fields": (
                "subscribed_at",
                "expires_at",
            )
        }),

        ("💳 Payment Details", {
            "fields": (
                "payment_required",
                "amount",
                "currency",
                "payment_id",
            )
        }),

        ("🛠 Admin Control", {
            "fields": (
                "subscribed_by_admin",
            )
        }),
    )

    actions = [
        "activate_subscription",
        "deactivate_subscription",
        "extend_subscription_30_days",
    ]

    # ================= ADMIN ACTIONS =================

    @admin.action(description="✅ Activate selected subscriptions")
    def activate_subscription(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="⛔ Deactivate selected subscriptions")
    def deactivate_subscription(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="⏳ Extend subscription by 30 days")
    def extend_subscription_30_days(self, request, queryset):
        now = timezone.now()
        for sub in queryset:
            if sub.expires_at and sub.expires_at > now:
                sub.expires_at += timezone.timedelta(days=30)
            else:
                sub.expires_at = now + timezone.timedelta(days=30)
            sub.is_active = True
            sub.save()


from django.contrib import admin
from .models import CourseCertificate


@admin.register(CourseCertificate)
class CourseCertificateAdmin(admin.ModelAdmin):

    list_display = (
        "certificate_id",
        "user",
        "course",
        "issued_at",
    )

    list_filter = (
        "course",
        "issued_at",
    )

    search_fields = (
        "certificate_id",
        "user__username",
        "user__email",
        "course__title",
    )

    readonly_fields = (
        "certificate_id",
        "issued_at",
    )

    ordering = ("-issued_at",)

    autocomplete_fields = (
        "user",
        "course",
    )