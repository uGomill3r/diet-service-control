"""
Vista mensual de pedidos y entregas.
Muestra un calendario con grilla semanal (lunes a viernes) que permite
navegar rápidamente a la vista semanal detallada.
"""
import calendar
import logging
from datetime import date

from django.shortcuts import render

from apps.core.decorators import protegido
from apps.core.models import Entrega, Pedido
from apps.core.utils import normalizar_fecha

logger = logging.getLogger(__name__)

# Nombres de meses en español
MESES_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Cabecera solo días hábiles (lunes → viernes)
CABECERA_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie"]


def _estado_color(pedido: int, entrega: int, fecha: date, hoy: date) -> str:
    """
    Devuelve el color Bootstrap para el badge de almuerzo o cena.
    - light   → sin pedido
    - success → entregado
    - danger  → no entregado (fecha pasada)
    - warning → pendiente (fecha futura o hoy)
    """
    if pedido == 0:
        return "light"
    if entrega == 1:
        return "success"
    if fecha < hoy:
        return "danger"
    return "warning"


@protegido
def vista_mensual(request):
    """Muestra el calendario mensual (lun-vie) con estado de pedidos por día."""
    hoy = date.today()

    # Leer parámetros de URL, con valores por defecto al mes actual
    try:
        mes = int(request.GET.get("mes", hoy.month))
        anio = int(request.GET.get("anio", hoy.year))
        if not (1 <= mes <= 12):
            mes = hoy.month
        if not (2000 <= anio <= 2100):
            anio = hoy.year
    except (ValueError, TypeError):
        mes = hoy.month
        anio = hoy.year

    logger.info("Cargando vista mensual — %d/%d", mes, anio)

    # Primer y último día del mes
    primer_dia = date(anio, mes, 1)
    ultimo_dia = date(anio, mes, calendar.monthrange(anio, mes)[1])

    # Pedidos del mes
    pedidos_qs = Pedido.objects.filter(
        fecha__range=(primer_dia, ultimo_dia)
    ).values("fecha", "almuerzo", "cena", "feriado")
    pedidos = {
        normalizar_fecha(row["fecha"]): {
            "almuerzo": row["almuerzo"] or 0,
            "cena": row["cena"] or 0,
            "feriado": row["feriado"],
        }
        for row in pedidos_qs
    }

    # Entregas del mes
    entregas_qs = Entrega.objects.filter(
        fecha__range=(primer_dia, ultimo_dia)
    ).values("fecha", "entregado_almuerzo", "entregado_cena")
    entregas = {
        normalizar_fecha(row["fecha"]): (
            row["entregado_almuerzo"] or 0,
            row["entregado_cena"] or 0,
        )
        for row in entregas_qs
    }

    # calendar.monthcalendar devuelve semanas con 0 = día fuera del mes
    # Cada fila tiene 7 elementos (lun=0 … dom=6); nos quedamos solo índices 0-4
    cal_matrix = calendar.monthcalendar(anio, mes)
    semanas = []

    for fila in cal_matrix:
        dias_habiles = fila[0:5]  # solo lunes a viernes

        # Si todos los días hábiles son 0, no hay días del mes en esta semana → omitir
        if all(n == 0 for n in dias_habiles):
            logger.debug("Semana omitida — sin días hábiles en el mes")
            continue

        dias_semana = []
        numero_semana = None

        for idx, num_dia in enumerate(dias_habiles):
            if num_dia == 0:
                dias_semana.append(None)
                continue

            fecha_dia = date(anio, mes, num_dia)

            if numero_semana is None:
                numero_semana = fecha_dia.isocalendar().week

            pedido = pedidos.get(fecha_dia, {"almuerzo": 0, "cena": 0, "feriado": False})
            entrega = entregas.get(fecha_dia, (0, 0))

            estado = {
                "almuerzo": _estado_color(pedido["almuerzo"], entrega[0], fecha_dia, hoy),
                "cena": _estado_color(pedido["cena"], entrega[1], fecha_dia, hoy),
            }

            dias_semana.append({
                "numero": num_dia,
                "fecha": fecha_dia.strftime("%d-%m-%Y"),
                "nombre_corto": CABECERA_SEMANA[idx],
                "en_mes": True,
                "es_hoy": fecha_dia == hoy,
                "feriado": pedido["feriado"],
                "estado": estado,
            })

        semanas.append({
            "numero": numero_semana,
            "dias": dias_semana,
        })

    logger.debug(
        "Vista mensual generada: %d semanas, %d pedidos cargados",
        len(semanas),
        len(pedidos),
    )

    # Navegación mes anterior / siguiente
    if mes == 1:
        mes_ant, anio_ant = 12, anio - 1
    else:
        mes_ant, anio_ant = mes - 1, anio

    if mes == 12:
        mes_sig, anio_sig = 1, anio + 1
    else:
        mes_sig, anio_sig = mes + 1, anio

    return render(
        request,
        "mes.html",
        {
            "semanas": semanas,
            "nombre_mes": MESES_ES[mes],
            "mes": mes,
            "anio": anio,
            "cabecera_semana": CABECERA_SEMANA,
            "mes_anterior": {"mes": mes_ant, "anio": anio_ant},
            "mes_siguiente": {"mes": mes_sig, "anio": anio_sig},
        },
    )