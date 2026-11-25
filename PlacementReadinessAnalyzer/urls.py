from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import login_view

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", login_view, name="root"),
    path("", include("accounts.urls")),
    path("", include("skills_evidence.urls")),
    path("", include("drives_readiness.urls")),
    path("", include("helpdesk.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)