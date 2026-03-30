"""
Vistas de autenticación.
Migrado desde blueprints/auth.py de Flask.
"""
import logging
import os
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from apps.core.models import Credencial

logger = logging.getLogger(__name__)


def credencial_valida(usuario, clave):
    """
    Verifica si las credenciales son válidas.
    Primero busca en la tabla credenciales, luego en variables de entorno.
    """
    logger.debug("Verificando credenciales para usuario: %s", usuario)
    try:
        cred = Credencial.objects.get(usuario=usuario)
        es_valida = clave == cred.contrasena
        logger.info("Credencial en BD para '%s': %s", usuario, "válida" if es_valida else "inválida")
        return es_valida
    except Credencial.DoesNotExist:
        # Fallback a variables de entorno
        app_user = os.environ.get("APP_USER", "")
        app_password = os.environ.get("APP_PASSWORD", "")
        es_valida = usuario == app_user and clave == app_password
        logger.info("Credencial ENV para '%s': %s", usuario, "válida" if es_valida else "inválida")
        return es_valida


def login(request):
    """Vista de inicio de sesión."""
    if request.method == "POST":
        usuario = request.POST.get("usuario", "")
        clave = request.POST.get("clave", "")

        if credencial_valida(usuario, clave):
            request.session["autenticado"] = True
            request.session["usuario"] = usuario
            # Si la clave coincide con la contraseña de entorno, es temporal
            app_password = os.environ.get("APP_PASSWORD", "")
            if clave == app_password:
                request.session["clave_temporal"] = True
                logger.info("Usuario '%s' inició sesión con clave temporal", usuario)
            else:
                request.session.pop("clave_temporal", None)
                logger.info("Usuario '%s' inició sesión correctamente", usuario)
            return redirect(reverse("dashboard"))

        logger.warning("Intento de login fallido para usuario: %s", usuario)
        messages.error(request, "Credenciales incorrectas")

    return render(request, "login.html", {"messages": messages.get_messages(request)})


def logout(request):
    """Cierra la sesión del usuario."""
    usuario = request.session.get("usuario", "desconocido")
    request.session.flush()
    logger.info("Usuario '%s' cerró sesión", usuario)
    return redirect(reverse("login"))


def recuperar(request):
    """Restaura la contraseña al valor predeterminado del entorno."""
    if request.method == "POST":
        app_user = os.environ.get("APP_USER", "")
        app_password = os.environ.get("APP_PASSWORD", "")

        logger.info("Restaurando contraseña para usuario: %s", app_user)
        Credencial.objects.update_or_create(
            usuario=app_user,
            defaults={"contrasena": app_password, "actualizado": timezone.now()},
        )
        messages.success(request, "Contraseña restaurada. Por favor inicia sesión y cámbiala.")
        return redirect(reverse("login"))

    return render(request, "recuperar.html", {"messages": messages.get_messages(request)})


def cambiar_clave(request):
    """Permite cambiar la contraseña desde una clave temporal."""
    if not request.session.get("autenticado"):
        return redirect(reverse("login"))

    if request.method == "POST":
        nueva = request.POST.get("nueva_clave", "")
        app_password = os.environ.get("APP_PASSWORD", "")

        if nueva == app_password:
            messages.error(request, "La nueva contraseña no puede ser igual a la inicial.")
            return render(request, "cambiar_clave.html", {"messages": messages.get_messages(request)})

        usuario = request.session.get("usuario", os.environ.get("APP_USER", ""))
        logger.info("Cambiando contraseña para usuario: %s", usuario)

        Credencial.objects.update_or_create(
            usuario=usuario,
            defaults={"contrasena": nueva, "actualizado": timezone.now()},
        )
        request.session.pop("clave_temporal", None)
        messages.success(request, "Contraseña actualizada correctamente.")
        return redirect(reverse("dashboard"))

    return render(request, "cambiar_clave.html", {"messages": messages.get_messages(request)})
