from django.urls import path
from . import views

urlpatterns = [
    path("semana", views.vista_semanal, name="semana"),
]
