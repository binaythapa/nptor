from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from quiz.urls.admin import urlpatterns as admin_urls

urlpatterns = [
    path("admin/", admin.site.urls),

    # ==============================
    # APPS
    # ==============================
    path("accounts/", include("accounts.urls")),
    path("quiz/", include("quiz.urls")),
    path("courses/", include("courses.urls")),
    path("", include("pages.urls")),   # 👈 homepage lives here
    path("org/", include("organizations.urls")), 
    path("api/", include("quiz.api_urls")),
]
urlpatterns += admin_urls
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
