from django.urls import path
from . import views

urlpatterns = [
    path("login", views.login, name="login"),
    path("logout", views.logout, name="logout"),
    path("recuperar", views.recuperar, name="recuperar"),
    path("cambiar_clave", views.cambiar_clave, name="cambiar_clave"),
]
