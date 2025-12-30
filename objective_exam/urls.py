from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from quiz.urls.admin import urlpatterns as admin_urls

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/', include('django.contrib.auth.urls')),

    # ✅ include quiz urls (folder-based)
    path('quiz/', include('quiz.urls')),

    path('api/', include('quiz.api_urls')),

    # Default redirect
    path('', RedirectView.as_view(
        pattern_name='quiz:practice',
        permanent=False
    )),
]

# extra admin urls
urlpatterns += admin_urls

# static & media
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
