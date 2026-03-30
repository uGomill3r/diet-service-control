"""
Decoradores de autenticación, equivalentes a decoradores.py de Flask.
Usa la sesión de Django en lugar de Flask session.
"""
import logging
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse

logger = logging.getLogger(__name__)


def protegido(view_func):
    """
    Requiere que el usuario esté autenticado en la sesión.
    Redirige a login si no hay sesión activa.
    Redirige a cambiar_clave si la clave es temporal.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("autenticado"):
            logger.debug("Acceso denegado a %s — sesión no autenticada", request.path)
            return redirect(reverse("login"))
        if request.session.get("clave_temporal"):
            logger.debug("Redirigiendo a cambio de clave temporal para %s", request.path)
            return redirect(reverse("cambiar_clave"))
        return view_func(request, *args, **kwargs)
    return wrapper
