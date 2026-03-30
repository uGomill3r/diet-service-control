from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("dashboard", views.dashboard, name="dashboard"),
    path("pedidos_siguientes", views.pedidos_siguientes, name="pedidos_siguientes"),
]
