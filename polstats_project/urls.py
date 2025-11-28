"""
URL configuration for polstats_project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('polstats_project.disclosures.urls')),
]
