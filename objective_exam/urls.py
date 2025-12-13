from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from quiz.views import *
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('quiz/', include('quiz.urls')),
    path('api/', include('quiz.api_urls')),
    #path('', RedirectView.as_view(pattern_name='quiz:exam_list', permanent=False)),
    path('', RedirectView.as_view(pattern_name='quiz:practice_express', permanent=False)),


   
]
urlpatterns += static(settings.STATIC_URL, document_root= settings.STATIC_ROOT)
urlpatterns +=  static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
