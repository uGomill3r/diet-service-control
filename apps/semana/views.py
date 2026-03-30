"""
Vista semanal de pedidos y entregas.
Migrado desde blueprints/semana.py de Flask.
"""
import logging
from datetime import datetime
from django.shortcuts import render
from apps.core.decorators import protegido
from apps.core.models import Pedido, Entrega
from apps.core.utils import (
    obtener_fechas_semana,
    normalizar_fecha,
    normalizar_fecha_ddmmaaaa,
    estado_textual,
)

logger = logging.getLogger(__name__)


@protegido
def vista_semanal(request):
    """Muestra el estado de pedidos y entregas de la semana seleccionada."""
    semana_actual = int(
        request.GET.get("semana", datetime.now().isocalendar().week)
    )
    logger.info("Cargando vista semanal — semana ISO: %d", semana_actual)

    dias, fechas = obtener_fechas_semana(semana_actual)

    fecha_inicio = normalizar_fecha_ddmmaaaa(fechas[0])
    fecha_fin = normalizar_fecha_ddmmaaaa(fechas[-1])

    # Pedidos de la semana
    pedidos_qs = Pedido.objects.filter(
        fecha__range=(fecha_inicio, fecha_fin)
    ).values("fecha", "almuerzo", "cena", "feriado")
    pedidos = {
        normalizar_fecha(row["fecha"]): {
            "almuerzo": row["almuerzo"] or 0,
            "cena": row["cena"] or 0,
            "feriado": row["feriado"],
        }
        for row in pedidos_qs
    }

    # Todas las entregas (para cruzar con los pedidos)
    entregas_qs = Entrega.objects.values("fecha", "entregado_almuerzo", "entregado_cena")
    entregas = {
        normalizar_fecha(row["fecha"]): (row["entregado_almuerzo"] or 0, row["entregado_cena"] or 0)
        for row in entregas_qs
    }

    hoy = datetime.now().date()
    semana_data = []

    for i, fecha_str in enumerate(fechas):
        fecha_obj = normalizar_fecha_ddmmaaaa(fecha_str)
        pedido = pedidos.get(fecha_obj, {"almuerzo": 0, "cena": 0, "feriado": False})
        entrega = entregas.get(fecha_obj, (0, 0))

        estado = {}
        for comida, p, e in zip(
            ["almuerzo", "cena"],
            [pedido["almuerzo"], pedido["cena"]],
            entrega,
        ):
            if p == 0:
                color = "light"
            elif e == 1:
                color = "success"
            elif fecha_obj < hoy:
                color = "danger"
            else:
                color = "warning"
            estado[comida] = color

        texto_estado = estado_textual(
            fecha_obj,
            (pedido["almuerzo"], pedido["cena"]),
            entrega,
            pedido["feriado"],
        )

        semana_data.append(
            {
                "dia": dias[i],
                "fecha": fecha_str,
                "estado": estado,
                "feriado": pedido["feriado"],
                "texto_estado": texto_estado,
            }
        )

    logger.debug("Vista semanal generada con %d días", len(semana_data))
    return render(
        request,
        "semana.html",
        {"semana": semana_actual, "semana_data": semana_data},
    )
