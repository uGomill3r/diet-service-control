from django.urls import path
from . import views

urlpatterns = [
    path("ver_dia", views.ver_dia, name="ver_dia"),
    path("editar_dia", views.editar_dia, name="editar_dia"),
    path("sugerencias_plato", views.sugerencias_plato, name="sugerencias_plato"),
]
