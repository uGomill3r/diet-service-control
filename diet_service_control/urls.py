"""
URLs principales del proyecto DietServiceControl.
"""
from django.urls import path, include

urlpatterns = [
    path("", include("apps.auth_app.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.mes.urls")),
    path("", include("apps.semana.urls")),
    path("", include("apps.dia.urls")),
    path("", include("apps.pagos.urls")),
    path("", include("apps.reportes.urls")),
    path("", include("apps.log.urls")),
    path("", include("apps.importar.urls")),
]
