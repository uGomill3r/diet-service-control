from django.urls import path
from . import views

urlpatterns = [
    path("importar", views.importar_eml, name="importar"),
    path("importar/confirmar", views.confirmar_importacion, name="confirmar_importacion"),
]
