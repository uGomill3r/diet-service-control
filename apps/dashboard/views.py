"""
Vistas del dashboard principal.
Migrado desde blueprints/dashboard.py de Flask.
"""
import logging
from datetime import datetime
from django.db.models import Q, Sum
from django.shortcuts import render, redirect
from django.urls import reverse
from apps.core.decorators import protegido
from apps.core.models import Pedido, Entrega, Pago, CicloPago
from apps.core.utils import normalizar_fecha, formatear_fecha_con_dia

logger = logging.getLogger(__name__)


def index(request):
    """Raíz del sitio: redirige según estado de sesión."""
    if not request.session.get("autenticado"):
        return redirect(reverse("login"))
    if request.session.get("clave_temporal"):
        return redirect(reverse("cambiar_clave"))
    return redirect(reverse("dashboard"))


def _ciclo_vigente(tipo, hoy):
    """
    Devuelve el ciclo de pago vigente para un tipo ('almuerzo' o 'cena').

    Vigente = fecha_inicio <= hoy y (fecha_fin nula o fecha_fin >= hoy).
    Si ninguno contiene la fecha de hoy (p. ej. el ciclo ya cerró), usa el
    último ciclo ya iniciado. Devuelve None si no hay ciclos.
    """
    base = CicloPago.objects.filter(tipo=tipo, fecha_inicio__lte=hoy).order_by("-fecha_inicio")
    ciclo = base.filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy)).first()
    if ciclo is None:
        ciclo = base.first()
        if ciclo is not None:
            logger.warning(
                "Ningún ciclo '%s' contiene %s — usando el último (id=%d)",
                tipo, hoy, ciclo.id,
            )
    logger.debug("Ciclo vigente '%s': %s", tipo, ciclo.id if ciclo else None)
    return ciclo


def _rango_ciclo(ciclo):
    """Devuelve (inicio, fin) del ciclo; sin ciclo, rango abierto desde la fecha mínima."""
    if ciclo is None:
        return datetime.min.date(), None
    return normalizar_fecha(ciclo.fecha_inicio), (
        normalizar_fecha(ciclo.fecha_fin) if ciclo.fecha_fin else None
    )


def _en_rango(fecha, inicio, fin):
    """True si la fecha está dentro de [inicio, fin] (fin None = sin límite)."""
    return fecha >= inicio and (fin is None or fecha <= fin)


def _pagos_ciclo(tipo, ciclo):
    """Suma la cantidad pagada asociada al ciclo (por FK, no por fecha del pago)."""
    if ciclo is None:
        return Pago.objects.filter(tipo=tipo).aggregate(total=Sum("cantidad"))["total"] or 0
    return Pago.objects.filter(ciclo=ciclo).aggregate(total=Sum("cantidad"))["total"] or 0


@protegido
def dashboard(request):
    """Vista principal del resumen de pedidos, entregas y pagos."""
    logger.info("Cargando dashboard")

    hoy_date = datetime.now().date()

    # Ciclo vigente por tipo (respeta fecha_fin editada manualmente)
    ciclo_alm = _ciclo_vigente("almuerzo", hoy_date)
    ciclo_cen = _ciclo_vigente("cena", hoy_date)
    alm_ini, alm_fin = _rango_ciclo(ciclo_alm)
    cen_ini, cen_fin = _rango_ciclo(ciclo_cen)
    logger.debug(
        "Rangos — almuerzo: %s a %s, cena: %s a %s",
        alm_ini, alm_fin, cen_ini, cen_fin,
    )

    # Pagos asociados a cada ciclo vigente
    pagos_alm = _pagos_ciclo("almuerzo", ciclo_alm)
    pagos_cen = _pagos_ciclo("cena", ciclo_cen)

    # Todos los pedidos y entregas
    pedidos_qs = Pedido.objects.values_list("fecha", "almuerzo", "cena")
    entregas_qs = Entrega.objects.values_list("fecha", "entregado_almuerzo", "entregado_cena")
    entregas = {normalizar_fecha(row[0]): (row[1] or 0, row[2] or 0) for row in entregas_qs}

    alm_pedidos = alm_entregados = alm_por_entregar = 0
    cen_pedidos = cen_entregados = cen_por_entregar = 0
    pedidos_pendientes_raw = []
    pedidos_por_validar_raw = []

    for fecha_iso, a_pedido, c_pedido in pedidos_qs:
        fecha_date = normalizar_fecha(fecha_iso)
        a_entregado, c_entregado = entregas.get(fecha_date, (0, 0))
        a_pedido = a_pedido or 0
        c_pedido = c_pedido or 0

        if _en_rango(fecha_date, alm_ini, alm_fin):
            alm_pedidos += a_pedido
            alm_entregados += a_entregado
            if a_pedido and not a_entregado and fecha_date >= hoy_date:
                alm_por_entregar += 1

        if _en_rango(fecha_date, cen_ini, cen_fin):
            cen_pedidos += c_pedido
            cen_entregados += c_entregado
            if c_pedido and not c_entregado and fecha_date >= hoy_date:
                cen_por_entregar += 1

        errores = []
        if a_pedido and not a_entregado:
            errores.append("almuerzo")
        if c_pedido and not c_entregado:
            errores.append("cena")
        if errores:
            if fecha_date >= hoy_date:
                pedidos_pendientes_raw.append((fecha_date, errores))
            else:
                pedidos_por_validar_raw.append((fecha_date, errores))

    # Formatear listas de pendientes
    pedidos_pendientes = [
        (f.strftime("%d-%m-%Y"), formatear_fecha_con_dia(f), e)
        for f, e in sorted(pedidos_pendientes_raw, key=lambda x: x[0])[:5]
    ]
    pedidos_por_validar = [
        (f.strftime("%d-%m-%Y"), formatear_fecha_con_dia(f), e)
        for f, e in sorted(pedidos_por_validar_raw, key=lambda x: x[0])[:5]
    ]

    alm_saldo = pagos_alm - alm_entregados - alm_por_entregar
    cen_saldo = pagos_cen - cen_entregados - cen_por_entregar

    fecha_ultimo_pago = alm_ini.strftime("%d-%m-%Y") if ciclo_alm else "—"
    logger.info(
        "Dashboard cargado — alm saldo: %d, cen saldo: %d, pendientes: %d",
        alm_saldo, cen_saldo, len(pedidos_pendientes_raw),
    )

    return render(
        request,
        "dashboard.html",
        {
            "alm_pagados": pagos_alm,
            "cen_pagados": pagos_cen,
            "alm_pedidos": alm_pedidos,
            "cen_pedidos": cen_pedidos,
            "alm_entregados": alm_entregados,
            "cen_entregados": cen_entregados,
            "alm_por_entregar": alm_por_entregar,
            "cen_por_entregar": cen_por_entregar,
            "alm_saldo": alm_saldo,
            "cen_saldo": cen_saldo,
            "fecha_ultimo_pago": fecha_ultimo_pago,
            "pedidos_pendientes": pedidos_pendientes,
            "pedidos_por_validar": pedidos_por_validar,
        },
    )


@protegido
def pedidos_siguientes(request):
    """Lista completa de pedidos futuros aún no entregados."""
    logger.info("Cargando pedidos siguientes")

    pedidos_qs = Pedido.objects.values_list("fecha", "almuerzo", "cena")
    entregas_qs = Entrega.objects.values_list("fecha", "entregado_almuerzo", "entregado_cena")
    entregas = {normalizar_fecha(row[0]): (row[1] or 0, row[2] or 0) for row in entregas_qs}

    hoy_date = datetime.now().date()
    pedidos = []

    for fecha_iso, a_pedido, c_pedido in pedidos_qs:
        fecha_date = normalizar_fecha(fecha_iso)
        a_entregado, c_entregado = entregas.get(fecha_date, (0, 0))
        a_pedido = a_pedido or 0
        c_pedido = c_pedido or 0

        errores_almuerzo = bool(a_pedido and not a_entregado and fecha_date >= hoy_date)
        errores_cena = bool(c_pedido and not c_entregado and fecha_date >= hoy_date)

        if errores_almuerzo or errores_cena:
            pedidos.append(
                {
                    "fecha_raw": fecha_date.strftime("%d-%m-%Y"),
                    "fecha_fmt": formatear_fecha_con_dia(fecha_date),
                    "almuerzo": errores_almuerzo,
                    "cena": errores_cena,
                }
            )

    pedidos.sort(key=lambda p: datetime.strptime(p["fecha_raw"], "%d-%m-%Y"))
    logger.info("Pedidos siguientes encontrados: %d", len(pedidos))

    return render(request, "pedidos_siguientes.html", {"pedidos": pedidos})