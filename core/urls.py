"""
URL configuration for core project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("select2/", include("django_select2.urls")),
]

# Настраиваем раздачу медиа-файлов (загруженных изображений)
# через Django-сервер в режиме отладки (DEBUG=True).
# В production-среде этим должен заниматься веб-сервер (например, Nginx).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)