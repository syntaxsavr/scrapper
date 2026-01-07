import os
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# URL patterns
urlpatterns = [
    path('admin/', admin.site.urls),        # Include the admin routes
    path('', include('webscraper.urls')),   # Include the webscraper app routes
]

# Add media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Add Sentry test route in development environment
if ENVIRONMENT == 'development':
    def trigger_error(request):
        _ = 1 / 0

    urlpatterns += [
        path('sentry-debug/', trigger_error),
    ]
