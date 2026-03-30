from django.urls import path
from . import views

urlpatterns = [
    path("pagos", views.pagos, name="pagos"),
    path("pagos/editar/<int:id>", views.editar_pago, name="editar_pago"),
]
