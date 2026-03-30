"""
Vista del changelog del proyecto.
Migrado desde blueprints/log.py de Flask.
"""
import logging
import re
import os
from django.shortcuts import render
from apps.core.decorators import protegido

logger = logging.getLogger(__name__)

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "changelog", "log.md")


@protegido
def log(request):
    """Muestra el contenido del changelog en pantalla."""
    logger.info("Cargando vista de changelog desde: %s", LOG_PATH)
    try:
        with open(LOG_PATH, encoding="utf-8") as f:
            contenido = f.read()
        # Convertir fechas ISO a formato DD-MM-YYYY para mostrar
        contenido = re.sub(r"(\d{4})-(\d{2})-(\d{2})", r"\3-\2-\1", contenido)
    except FileNotFoundError:
        logger.warning("Archivo de changelog no encontrado: %s", LOG_PATH)
        contenido = "Registro no disponible."

    return render(request, "log.html", {"contenido": contenido})
