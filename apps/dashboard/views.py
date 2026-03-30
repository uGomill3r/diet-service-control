"""
Vistas del dashboard principal.
Migrado desde blueprints/dashboard.py de Flask.
"""
import logging
from datetime import datetime
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


@protegido
def dashboard(request):
    """Vista principal del resumen de pedidos, entregas y pagos."""
    logger.info("Cargando dashboard")

    # Obtener fecha de inicio del último ciclo por tipo
    from django.db.models import Max
    ciclos_qs = CicloPago.objects.values("tipo").annotate(max_inicio=Max("fecha_inicio"))
    ciclos = {c["tipo"]: c["max_inicio"] for c in ciclos_qs}

    fecha_min = datetime.min.date()
    alm_ciclo = ciclos.get("almuerzo", fecha_min)
    cen_ciclo = ciclos.get("cena", fecha_min)
    logger.debug("Ciclos activos — almuerzo: %s, cena: %s", alm_ciclo, cen_ciclo)

    # Pagos desde inicio de cada ciclo
    from django.db.models import Sum
    pagos_alm = Pago.objects.filter(tipo="almuerzo", fecha__gte=alm_ciclo).aggregate(
        total=Sum("cantidad")
    )["total"] or 0
    pagos_cen = Pago.objects.filter(tipo="cena", fecha__gte=cen_ciclo).aggregate(
        total=Sum("cantidad")
    )["total"] or 0

    # Todos los pedidos y entregas
    pedidos_qs = Pedido.objects.values_list("fecha", "almuerzo", "cena")
    entregas_qs = Entrega.objects.values_list("fecha", "entregado_almuerzo", "entregado_cena")
    entregas = {normalizar_fecha(row[0]): (row[1] or 0, row[2] or 0) for row in entregas_qs}

    hoy_date = datetime.now().date()
    alm_pedidos = alm_entregados = alm_por_entregar = 0
    cen_pedidos = cen_entregados = cen_por_entregar = 0
    pedidos_pendientes_raw = []
    pedidos_por_validar_raw = []

    for fecha_iso, a_pedido, c_pedido in pedidos_qs:
        fecha_date = normalizar_fecha(fecha_iso)
        a_entregado, c_entregado = entregas.get(fecha_date, (0, 0))
        a_pedido = a_pedido or 0
        c_pedido = c_pedido or 0

        if fecha_date >= alm_ciclo:
            alm_pedidos += a_pedido
            alm_entregados += a_entregado
            if a_pedido and not a_entregado and fecha_date >= hoy_date:
                alm_por_entregar += 1

        if fecha_date >= cen_ciclo:
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

    fecha_ultimo_pago = alm_ciclo.strftime("%d-%m-%Y") if alm_ciclo != fecha_min else "—"
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
