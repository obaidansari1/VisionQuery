from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from uploads.views import IndexView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("uploads.urls")),
    path("", IndexView.as_view(), name="index"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
