"""
Vistas para importar el plan de almuerzos desde un archivo .eml
generado por Google Forms.

Flujo:
1. GET /importar  → formulario de subida del .eml
2. POST /importar → parsea el .eml y muestra previsualización
3. POST /importar/confirmar → guarda los pedidos en la BD
"""
import json
import logging
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from apps.core.decorators import protegido
from apps.core.models import Pedido
from .parser import parsear_eml

logger = logging.getLogger(__name__)


@protegido
def importar_eml(request):
    """
    GET: muestra el formulario de subida.
    POST: parsea el .eml y muestra la previsualización.
    """
    if request.method == "POST":
        archivo = request.FILES.get("archivo_eml")

        if not archivo:
            messages.error(request, "Debes seleccionar un archivo .eml.")
            return render(request, "importar.html", {"messages": messages.get_messages(request)})

        if not archivo.name.lower().endswith(".eml"):
            messages.error(request, "El archivo debe tener extensión .eml.")
            return render(request, "importar.html", {"messages": messages.get_messages(request)})

        logger.info("Archivo .eml recibido: %s (%d bytes)", archivo.name, archivo.size)
        contenido = archivo.read()
        resultado = parsear_eml(contenido)

        if not resultado["dias"]:
            messages.error(
                request,
                "No se pudieron extraer días del archivo. "
                "Verifica que sea el recibo de respuesta de Google Forms.",
            )
            return render(request, "importar.html", {"messages": messages.get_messages(request)})

        # Verificar qué fechas ya tienen pedido en la BD para mostrar advertencia
        fechas_con_pedido = set()
        fechas_validas = [d["fecha"] for d in resultado["dias"] if d["fecha"]]
        if fechas_validas:
            existentes = Pedido.objects.filter(
                fecha__in=fechas_validas
            ).values_list("fecha", flat=True)
            fechas_con_pedido = {f for f in existentes}
            logger.info(
                "Fechas con pedido existente: %d de %d",
                len(fechas_con_pedido), len(fechas_validas),
            )

        # Marcar cada día si ya existe
        for dia in resultado["dias"]:
            dia["ya_existe"] = dia["fecha"] in fechas_con_pedido if dia["fecha"] else False

        # Serializar para pasar al formulario de confirmación
        # Solo guardamos lo necesario para el confirm
        datos_confirmacion = [
            {
                "dia": d["dia"],
                "fecha": d["fecha"].isoformat() if d["fecha"] else None,
                "entrada": d["entrada"],
                "fondo": d["fondo"],
            }
            for d in resultado["dias"]
            if d["fecha"] and (d["entrada"] or d["fondo"])
        ]

        return render(
            request,
            "importar_preview.html",
            {
                "resultado": resultado,
                "datos_json": json.dumps(datos_confirmacion),
                "total_dias": len(resultado["dias"]),
                "con_errores": len(resultado["errores"]),
            },
        )

    return render(request, "importar.html", {"messages": messages.get_messages(request)})


@protegido
def confirmar_importacion(request):
    """
    POST: recibe el JSON de días confirmados y los guarda en la BD.
    Usa update_or_create para no borrar datos existentes de otros campos.
    """
    if request.method != "POST":
        return redirect(reverse("importar"))

    datos_json = request.POST.get("datos_json", "[]")

    try:
        dias = json.loads(datos_json)
    except json.JSONDecodeError:
        messages.error(request, "Error al procesar los datos. Intenta nuevamente.")
        return redirect(reverse("importar"))

    logger.info("Confirmando importación de %d días", len(dias))

    guardados = 0
    errores = 0

    for dia in dias:
        fecha_str = dia.get("fecha")
        entrada = dia.get("entrada") or ""
        fondo = dia.get("fondo") or ""

        if not fecha_str:
            continue

        from datetime import date
        try:
            from datetime import datetime
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Fecha inválida en confirmación: %s", fecha_str)
            errores += 1
            continue

        try:
            semana = fecha.isocalendar().week
            obj, created = Pedido.objects.update_or_create(
                fecha=fecha,
                defaults={
                    "semana": semana,
                    "almuerzo": 1,        # se marca como pedido de almuerzo
                    "entrada": entrada,
                    "fondo": fondo,
                },
            )
            accion = "creado" if created else "actualizado"
            logger.debug("Pedido %s para %s — entrada: %s, fondo: %s", accion, fecha, entrada, fondo)
            guardados += 1
        except Exception as e:
            logger.error("Error guardando pedido para %s: %s", fecha_str, e)
            errores += 1

    if guardados:
        messages.success(
            request,
            f"Importación completada: {guardados} día(s) guardado(s) correctamente."
            + (f" {errores} error(es)." if errores else ""),
        )
    else:
        messages.error(request, "No se guardó ningún día. Revisa los datos e intenta nuevamente.")

    logger.info("Importación finalizada — guardados: %d, errores: %d", guardados, errores)
    return redirect(reverse("dashboard"))
