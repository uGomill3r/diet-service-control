from django.urls import path
from . import views

urlpatterns = [
    path("reporte_ciclo", views.reporte_ciclo, name="reporte_ciclo"),
    path("ciclo_excel", views.ciclo_excel, name="ciclo_excel"),
]
