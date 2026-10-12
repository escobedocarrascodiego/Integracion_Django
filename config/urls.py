"""
URL configuration: the admin, the REST API under /api/, and the login page of
DRF's browsable API.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/chat/', include('chat.urls')),
    path('api/', include('municipal.urls')),
    path('api-auth/', include('rest_framework.urls')),
]
