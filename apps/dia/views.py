"""
Vistas para edición y visualización de un día específico.
Migrado desde blueprints/dia.py de Flask.
"""
import logging
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse
from apps.core.decorators import protegido
from apps.core.models import Pedido, Entrega
from apps.core.utils import normalizar_fecha, buscar_platos_similares

logger = logging.getLogger(__name__)


def siguiente_dia_habil(fecha):
    """Devuelve el siguiente día hábil (lunes a viernes)."""
    siguiente = fecha + timedelta(days=1)
    while siguiente.weekday() > 4:
        siguiente += timedelta(days=1)
    return siguiente


def anterior_dia_habil(fecha):
    """Devuelve el día hábil anterior (lunes a viernes)."""
    anterior = fecha - timedelta(days=1)
    while anterior.weekday() > 4:
        anterior -= timedelta(days=1)
    return anterior


def cargar_datos_dia(fecha_form):
    """
    Carga todos los datos de pedido y entrega para una fecha dada.
    Retorna un dict con todo lo necesario para el template.
    """
    logger.debug("Cargando datos del día: %s", fecha_form)
    fecha_obj = datetime.strptime(fecha_form, "%d-%m-%Y")
    dias_abreviados = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    dia_semana = dias_abreviados[fecha_obj.weekday()]
    fecha_con_dia = f"{dia_semana} {fecha_form}"
    fecha_date = fecha_obj.date()

    try:
        pedido_obj = Pedido.objects.get(fecha=fecha_date)
        pedido = (pedido_obj.almuerzo or 0, pedido_obj.cena or 0)
        feriado = pedido_obj.feriado or False
        obs_pedido = pedido_obj.observaciones or ""
        entrada = pedido_obj.entrada or ""
        fondo = pedido_obj.fondo or ""
        plato_cena = pedido_obj.plato_cena or ""
    except Pedido.DoesNotExist:
        pedido = (0, 0)
        feriado = False
        obs_pedido = entrada = fondo = plato_cena = ""

    try:
        entrega_obj = Entrega.objects.get(fecha=fecha_date)
        entrega = (
            entrega_obj.entregado_almuerzo or 0,
            entrega_obj.entregado_cena or 0,
            entrega_obj.observaciones or "",
        )
    except Entrega.DoesNotExist:
        entrega = (0, 0, "")

    fecha_ant = anterior_dia_habil(fecha_obj).strftime("%d-%m-%Y")
    fecha_sig = siguiente_dia_habil(fecha_obj).strftime("%d-%m-%Y")

    return {
        "fecha": fecha_form,
        "fecha_con_dia": fecha_con_dia,
        "pedido": pedido,
        "entrega": entrega,
        "feriado": feriado,
        "obs_pedido": obs_pedido,
        "entrada": entrada,
        "fondo": fondo,
        "plato_cena": plato_cena,
        "fecha_ant": fecha_ant,
        "fecha_sig": fecha_sig,
    }


@protegido
def ver_dia(request):
    """Muestra los datos de un día en modo solo lectura."""
    fecha_form = request.GET.get("fecha")
    if not fecha_form:
        return redirect(reverse("semana"))
    contexto = cargar_datos_dia(fecha_form)
    contexto["solo_lectura"] = True
    return render(request, "editar_dia.html", contexto)


@protegido
def editar_dia(request):
    """Permite editar pedido y entrega de un día específico."""
    if request.method == "POST":
        fecha_form = request.POST.get("fecha")
        fecha_date = datetime.strptime(fecha_form, "%d-%m-%Y").date()

        almuerzo = 1 if request.POST.get("almuerzo") == "on" else 0
        cena = 1 if request.POST.get("cena") == "on" else 0
        entrada = request.POST.get("entrada", "")
        fondo = request.POST.get("fondo", "")
        plato_cena = request.POST.get("plato_cena", "")
        obs_pedido = request.POST.get("obs_pedido", "")
        entregado_almuerzo = 1 if request.POST.get("entregado_almuerzo") == "on" else 0
        entregado_cena = 1 if request.POST.get("entregado_cena") == "on" else 0
        obs_entrega = request.POST.get("obs_entrega", "")
        feriado = request.POST.get("feriado") == "on"

        logger.info(
            "Guardando día %s — almuerzo=%d, cena=%d, feriado=%s",
            fecha_form, almuerzo, cena, feriado,
        )

        # Guardar o actualizar pedido
        semana = fecha_date.isocalendar().week
        Pedido.objects.update_or_create(
            fecha=fecha_date,
            defaults={
                "semana": semana,
                "almuerzo": almuerzo,
                "cena": cena,
                "feriado": feriado,
                "observaciones": obs_pedido,
                "entrada": entrada,
                "fondo": fondo,
                "plato_cena": plato_cena,
            },
        )

        # Guardar o actualizar entrega
        Entrega.objects.update_or_create(
            fecha=fecha_date,
            defaults={
                "entregado_almuerzo": entregado_almuerzo,
                "entregado_cena": entregado_cena,
                "observaciones": obs_entrega,
            },
        )

        accion = request.POST.get("accion")
        if accion == "guardar_siguiente":
            fecha_actual = datetime.strptime(fecha_form, "%d-%m-%Y")
            siguiente = siguiente_dia_habil(fecha_actual)
            siguiente_str = siguiente.strftime("%d-%m-%Y")
            logger.debug("Redirigiendo al siguiente día hábil: %s", siguiente_str)
            return redirect(f"{reverse('editar_dia')}?fecha={siguiente_str}")

        return redirect(reverse("semana"))

    # GET
    fecha_form = request.GET.get("fecha")
    if not fecha_form:
        return redirect(reverse("semana"))
    contexto = cargar_datos_dia(fecha_form)
    contexto["solo_lectura"] = False
    return render(request, "editar_dia.html", contexto)


@protegido
def sugerencias_plato(request):
    """API JSON para autocompletado de nombres de platos."""
    termino = request.GET.get("q", "")
    if not termino:
        return JsonResponse([], safe=False)

    resultados = buscar_platos_similares(termino)
    platos = set()
    for entrada, fondo, cena in resultados:
        for plato in [entrada, fondo, cena]:
            if plato and termino.lower() in plato.lower():
                platos.add(plato)

    logger.debug("Sugerencias para '%s': %d resultados", termino, len(platos))
    return JsonResponse(sorted(platos), safe=False)
