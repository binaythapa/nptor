from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from quiz.urls.admin import urlpatterns as admin_urls

urlpatterns = [
    path("admin/", admin.site.urls),

    # ==============================
    # APPS
    # ==============================
    path("accounts/", include("accounts.urls")),   # ✅ OTP login
    path("quiz/", include("quiz.urls")),
    path("courses/", include("courses.urls")),

    path("api/", include("quiz.api_urls")),

    # ==============================
    # DEFAULT REDIRECT
    # ==============================
    path(
        "",
        RedirectView.as_view(
            pattern_name="quiz:practice",
            permanent=False
        ),
    ),
]

# ==============================
# EXTRA ADMIN URLS
# ==============================
urlpatterns += admin_urls

# ==============================
# STATIC & MEDIA
# ==============================
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
