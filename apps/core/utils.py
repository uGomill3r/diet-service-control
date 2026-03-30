"""
Funciones utilitarias del proyecto, migradas desde utils.py de Flask.
"""
import logging
from datetime import datetime, date, timedelta
from apps.core.models import Pedido

logger = logging.getLogger(__name__)


def obtener_fechas_semana(numero_semana, año=None):
    """Devuelve los días abreviados y fechas de una semana ISO dada."""
    if año is None:
        año = datetime.now().isocalendar().year
    lunes = datetime.strptime(f"{año}-W{int(numero_semana):02}-1", "%G-W%V-%u")
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie"]
    fechas = [(lunes + timedelta(days=i)).strftime("%d-%m-%Y") for i in range(5)]
    return dias, fechas


def normalizar_fecha(fecha):
    """Convierte varios tipos de fecha a un objeto date de Python."""
    if isinstance(fecha, date) and not isinstance(fecha, datetime):
        return fecha
    if isinstance(fecha, datetime):
        return fecha.date()
    if isinstance(fecha, str):
        try:
            return datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Fecha en formato incorrecto: {fecha}")
    raise ValueError(f"Tipo de fecha no reconocido: {type(fecha)}")


def normalizar_fecha_ddmmaaaa(fecha_str):
    """Convierte una cadena 'DD-MM-YYYY' a objeto date."""
    return datetime.strptime(fecha_str, "%d-%m-%Y").date()


def formatear_fecha(fecha):
    """Formatea una fecha como 'DD-MM-YYYY'."""
    return normalizar_fecha(fecha).strftime("%d-%m-%Y")


def estado_textual(fecha_obj, pedido, entrega, feriado):
    """Genera texto descriptivo del estado de entrega de un día."""
    if feriado:
        return "Feriado"
    if pedido == (0, 0):
        return "Sin pedido registrado"
    a_pedido, c_pedido = pedido
    a_entregado, c_entregado = entrega
    pendientes = []
    if a_pedido and not a_entregado:
        pendientes.append("almuerzo")
    if c_pedido and not c_entregado:
        pendientes.append("cena")
    if pendientes and fecha_obj < datetime.now().date():
        return f"Entrega pendiente: {', '.join(pendientes)}"
    if not pendientes:
        return "Entregado"
    return ""


def buscar_platos_similares(nombre):
    """Busca platos similares en la base de datos usando el ORM de Django."""
    logger.debug("Buscando platos similares a: %s", nombre)
    resultados = (
        Pedido.objects.filter(
            entrada__icontains=nombre
        )
        .values_list("entrada", "fondo", "plato_cena")
        .union(
            Pedido.objects.filter(fondo__icontains=nombre).values_list(
                "entrada", "fondo", "plato_cena"
            )
        )
        .union(
            Pedido.objects.filter(plato_cena__icontains=nombre).values_list(
                "entrada", "fondo", "plato_cena"
            )
        )[:10]
    )
    logger.debug("Encontrados %d resultados para '%s'", len(list(resultados)), nombre)
    return resultados


def formatear_fecha_con_dia(fecha: date) -> str:
    """Devuelve la fecha con el día de la semana abreviado, e.g. 'Lun 01-03-2025'."""
    dias_abreviados = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    dia = dias_abreviados[fecha.weekday()]
    return f"{dia} {fecha.strftime('%d-%m-%Y')}"
