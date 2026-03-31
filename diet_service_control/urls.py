"""
URLs principales del proyecto DietServiceControl.
"""
from django.urls import path, include
from django.http import FileResponse
from pathlib import Path

# Sirve el ícono PNG desde la raíz para satisfacer las búsquedas automáticas de Safari/iOS
def _serve_touch_icon(request):
    icon_path = Path(__file__).resolve().parent.parent / "static" / "favicon.png"
    return FileResponse(open(icon_path, "rb"), content_type="image/png")

urlpatterns = [
    # Rutas requeridas por Safari/iOS al agregar a favoritos
    path("apple-touch-icon.png", _serve_touch_icon),
    path("apple-touch-icon-precomposed.png", _serve_touch_icon),
    path("favicon.ico", _serve_touch_icon),
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