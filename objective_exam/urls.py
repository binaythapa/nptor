from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from quiz.urls.admin import urlpatterns as admin_urls
from core.views.health import health_check


from django.http import HttpResponse

def ads_txt(request):
    return HttpResponse(
        "google.com, pub-5294449232420430, DIRECT, f08c47fec0942fa0",
        content_type="text/plain"
    )


urlpatterns = [
    path("ads.txt", ads_txt),
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("ckeditor/", include("ckeditor_uploader.urls")),

    # ==============================
    # APPS
    # ==============================
    path("accounts/", include("accounts.urls")),
    path("quiz/", include("quiz.urls")),
    path("courses/", include("courses.urls")),
    path("", include("pages.urls")),   # 👈 homepage lives here
    #path("org/", include("organizations.urls")), 
    path("org/<slug:slug>/", include("organizations.urls")),
    path("api/", include("quiz.api_urls")),
]
urlpatterns += admin_urls
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
