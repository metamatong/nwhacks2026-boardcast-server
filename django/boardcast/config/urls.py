from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/rooms/", include("rooms.urls")),
    path("api/media/", include("media_ingest.urls")),
    path("api/realtime/", include("realtime.urls")),
    path("api/", include("digitization.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
