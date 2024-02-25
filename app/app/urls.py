from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        'api/schema',
        SpectacularAPIView.as_view(),
        name='schema'
    ),
    path(
        'api/docs',
        SpectacularSwaggerView.as_view(),
        name='api-schema'
    ),
    path('api/user/', include('user.urls')),
    path('api/recipe/', include('recipe.urls'))
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
