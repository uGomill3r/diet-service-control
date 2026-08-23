"""
Parser del archivo .eml de confirmacion de pedido de menu enviado por
dietservice.pe (notificacion@dietservice.pe).

Estructura del email (parte text/html):
Una tabla plana con una fila <tr> por cada linea de comida. Cada fila tiene
3 <td>: fecha (solo en la primera fila del dia, ISO YYYY-MM-DD), tipo de
comida (Entrada/Fondo/Cena) y el plato seleccionado. Las filas siguientes
del mismo dia dejan la celda de fecha vacia.
"""
import email
import logging
import re
from datetime import date, datetime
from email import policy
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

# Tipos de comida reconocidos en la columna central de la tabla
TIPOS_COMIDA = {"entrada": "entrada", "fondo": "fondo", "cena": "cena"}


class PedidoMenuParser(HTMLParser):
    """
    Parser HTML que recorre la tabla del correo de dietservice.pe y arma
    una lista de filas {fecha_texto, tipo, plato} en orden de aparicion.

    Tambien captura el nombre del cliente desde el <h3>.
    """

    def __init__(self):
        super().__init__()
        self.filas = []            # lista de dicts {fecha_texto, tipo, plato}
        self.nombre = ""
        self._en_h3 = False
        self._nombre_buffer = ""
        self._en_tr = False
        self._en_td = False
        self._celdas_fila = []
        self._celda_buffer = ""

    def handle_starttag(self, tag, attrs):
        if tag == "h3" and not self.nombre:
            self._en_h3 = True
            self._nombre_buffer = ""
        if tag == "tr":
            self._en_tr = True
            self._celdas_fila = []
        if tag == "td" and self._en_tr:
            self._en_td = True
            self._celda_buffer = ""

    def handle_endtag(self, tag):
        if tag == "h3" and self._en_h3:
            self.nombre = self._nombre_buffer.strip()
            self._en_h3 = False
        if tag == "td" and self._en_td:
            self._celdas_fila.append(self._celda_buffer.strip())
            self._en_td = False
        if tag == "tr" and self._en_tr:
            if len(self._celdas_fila) == 3:
                fecha_texto, tipo_texto, plato = self._celdas_fila
                tipo = TIPOS_COMIDA.get(tipo_texto.strip().lower())
                if tipo and plato:
                    self.filas.append({
                        "fecha_texto": fecha_texto.strip(),
                        "tipo": tipo,
                        "plato": plato,
                    })
            self._en_tr = False

    def handle_data(self, data):
        if self._en_h3:
            self._nombre_buffer += data
        if self._en_td:
            self._celda_buffer += data


def _extraer_html(msg):
    """Extrae la parte text/html del mensaje email."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                return payload.decode(charset, errors="replace")
    else:
        if msg.get_content_type() == "text/html":
            charset = msg.get_content_charset() or "utf-8"
            return msg.get_payload(decode=True).decode(charset, errors="replace")
    return ""


def _decodificar_asunto(msg):
    """Decodifica el asunto del email, que puede venir en partes con distinto charset."""
    from email.header import decode_header

    asunto_raw = msg.get("Subject", "")
    partes = decode_header(asunto_raw)
    asunto = ""
    for parte, charset in partes:
        if isinstance(parte, bytes):
            asunto += parte.decode(charset or "utf-8", errors="replace")
        else:
            asunto += parte
    return asunto


def parsear_eml(contenido_bytes):
    """
    Parsea el contenido binario del .eml de confirmacion de pedido de menu
    (dietservice.pe) y extrae los platos seleccionados por dia.

    Retorna:
        {
            'asunto': str,
            'nombre': str,        # nombre del cliente detectado en el correo
            'dias': [
                {
                    'fecha': date,
                    'entrada': str | None,
                    'fondo': str | None,
                    'cena': str | None,   # plato de cena, si el dia lo incluye
                },
                ...
            ],
            'errores': [str],
        }
    """
    logger.info("Iniciando parseo de archivo .eml (%d bytes)", len(contenido_bytes))

    resultado = {
        "asunto": "",
        "nombre": "",
        "dias": [],
        "errores": [],
    }

    try:
        msg = email.message_from_bytes(contenido_bytes, policy=policy.compat32)
    except Exception as e:
        logger.error("Error al parsear el email: %s", e)
        resultado["errores"].append(f"No se pudo leer el archivo: {e}")
        return resultado

    asunto = _decodificar_asunto(msg)
    resultado["asunto"] = asunto
    logger.info("Asunto del email: %s", asunto)

    html = _extraer_html(msg)
    if not html:
        resultado["errores"].append("El archivo .eml no contiene contenido HTML.")
        logger.warning("No se encontro parte text/html en el .eml")
        return resultado

    logger.debug("HTML extraido: %d caracteres", len(html))

    parser = PedidoMenuParser()
    parser.feed(html)
    resultado["nombre"] = parser.nombre
    logger.info("Filas de tabla detectadas: %d, cliente: %s", len(parser.filas), parser.nombre)

    if not parser.filas:
        resultado["errores"].append(
            "No se pudo extraer la tabla de platos del correo. "
            "Verifica que sea el correo de confirmacion de pedido de menu."
        )
        return resultado

    # Agrupar filas por fecha, arrastrando la ultima fecha vista cuando la
    # celda de fecha viene vacia (filas de Fondo/Cena continuan el dia previo)
    dias_dict = {}
    orden_fechas = []
    fecha_actual = None

    for fila in parser.filas:
        if fila["fecha_texto"]:
            try:
                fecha_actual = datetime.strptime(fila["fecha_texto"], "%Y-%m-%d").date()
            except ValueError:
                logger.error("Fecha invalida en tabla: %s", fila["fecha_texto"])
                resultado["errores"].append(f"Fecha invalida en tabla: {fila['fecha_texto']}")
                fecha_actual = None
                continue

        if fecha_actual is None:
            logger.warning("Fila sin fecha asociada, se omite: %s", fila)
            continue

        if fecha_actual not in dias_dict:
            dias_dict[fecha_actual] = {"fecha": fecha_actual, "entrada": None, "fondo": None, "cena": None}
            orden_fechas.append(fecha_actual)

        dias_dict[fecha_actual][fila["tipo"]] = fila["plato"]

    dias_ordenados = [dias_dict[f] for f in sorted(orden_fechas)]
    resultado["dias"] = dias_ordenados

    logger.info(
        "Parseo completado: %d dias extraidos, %d errores",
        len(dias_ordenados), len(resultado["errores"]),
    )
    return resultado