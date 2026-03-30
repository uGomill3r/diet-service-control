"""
URLs de la vista mensual.
Registrar en diet_service_control/urls.py con:
    path("mes", include("apps.mes.urls")),
"""
from django.urls import path
from . import views

urlpatterns = [
    path("mes", views.vista_mensual, name="mes"),
]
