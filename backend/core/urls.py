# backend/core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="dashboard.html")),
    path("admin/", admin.site.urls),
    path("api/v1/", include("analytics.urls")),
]

