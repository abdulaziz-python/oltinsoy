from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from api.admin import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

