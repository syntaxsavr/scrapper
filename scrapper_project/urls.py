import os
from django.contrib import admin
from django.urls import path, include

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# URL patterns
urlpatterns = [
    path('admin/', admin.site.urls),        # Include the admin routes
    path('', include('webscraper.urls')),   # Include the webscraper app routes
]

# Add Sentry test route in development environment
if ENVIRONMENT == 'development':
    def trigger_error(request):
        division_by_zero = 1 / 0
        return

    urlpatterns += [
        path('sentry-debug/', trigger_error),
    ]
