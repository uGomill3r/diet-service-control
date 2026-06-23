"""
Parser del archivo .eml generado por Google Forms al completar el formulario
de Plan de Alimentación.

Estructura del email:
- Parte text/plain (base64): lista plana de opciones por día, la seleccionada
  aparece PRIMERO en cada bloque.
- Parte text/html: tiene aria-checked="true" en la opción elegida.

Usamos el HTML porque es más confiable para identificar la selección.
"""
import email
import logging
import re
from datetime import date
from email import policy
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

# Mapeo de nombres de mes en español a número
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


class FormResponseParser(HTMLParser):
    """
    Parser HTML que extrae las opciones seleccionadas (aria-checked=true)
    agrupadas por pregunta (DD Entrada / DD Fondo).
    """

    def __init__(self):
        super().__init__()
        self.preguntas = []          # lista de dicts {titulo, seleccionada, opciones}
        self._pregunta_actual = None
        self._capturando_titulo = False
        self._titulo_buffer = ""
        self._capturando_opcion = False
        self._opcion_buffer = ""
        self._opcion_checked = False
        self._dentro_td_opcion = False
        self._depth_td = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Detectar h2 que es título de pregunta
        if tag == "h2":
            self._capturando_titulo = True
            self._titulo_buffer = ""

        # Detectar div[role=radio] — cada opción de respuesta
        if tag == "div" and attrs_dict.get("role") == "radio":
            self._opcion_checked = attrs_dict.get("aria-checked") == "true"
            self._opcion_buffer = ""
            self._dentro_td_opcion = False

        # El texto de la opción está en el <td> que sigue al div radio
        if tag == "td":
            self._dentro_td_opcion = True
            self._capturando_opcion = True
            self._opcion_buffer = ""

    def handle_endtag(self, tag):
        if tag == "h2" and self._capturando_titulo:
            titulo = self._titulo_buffer.strip()
            # Solo nos interesan preguntas tipo "DD Entrada" o "DD Fondo"
            if re.match(r"^\d{2}\s+(Entrada|Fondo)$", titulo):
                self._pregunta_actual = {
                    "titulo": titulo,
                    "seleccionada": None,
                    "opciones": [],
                }
                self.preguntas.append(self._pregunta_actual)
            self._capturando_titulo = False

        if tag == "td" and self._dentro_td_opcion and self._capturando_opcion:
            texto = self._opcion_buffer.strip()
            if texto and self._pregunta_actual:
                self._pregunta_actual["opciones"].append(texto)
                if self._opcion_checked:
                    self._pregunta_actual["seleccionada"] = texto
            self._capturando_opcion = False
            self._dentro_td_opcion = False

    def handle_data(self, data):
        if self._capturando_titulo:
            self._titulo_buffer += data
        if self._capturando_opcion and self._dentro_td_opcion:
            self._opcion_buffer += data


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


def _extraer_año_del_asunto(asunto):
    """Intenta extraer el año desde el asunto del email."""
    match = re.search(r"\b(20\d{2})\b", asunto)
    if match:
        return int(match.group(1))
    return date.today().year


def _extraer_mes_del_asunto(asunto):
    """Extrae el número de mes desde el asunto del email.

    Retorna el primer mes encontrado (usado como fallback o cuando el plan
    es de un solo mes). Para planes que cruzan meses, usar
    _extraer_rango_meses_del_asunto.
    """
    asunto_lower = asunto.lower()
    for nombre, numero in MESES.items():
        if nombre in asunto_lower:
            return numero
    return None


def _extraer_rango_meses_del_asunto(asunto):
    """Extrae todos los meses mencionados en el asunto, en el orden en que aparecen.

    Retorna una lista de (nombre, numero) según su posición en el texto.
    Ejemplo: "del 29 de Junio al 10 de Julio" → [(6, pos_junio), (7, pos_julio)]
    ordenados por posición.
    """
    asunto_lower = asunto.lower()
    encontrados = []
    for nombre, numero in MESES.items():
        pos = asunto_lower.find(nombre)
        if pos != -1:
            encontrados.append((pos, numero))
    encontrados.sort()  # ordenar por posición de aparición en el texto
    return [numero for _, numero in encontrados]


def parsear_eml(contenido_bytes):
    """
    Parsea el contenido binario de un archivo .eml y extrae los platos
    seleccionados por día.

    Retorna:
        {
            'asunto': str,
            'año': int,
            'mes': int,
            'dias': [
                {
                    'dia': int,           # número de día del mes
                    'fecha': date,
                    'entrada': str,       # opción seleccionada para Entrada
                    'fondo': str,         # opción seleccionada para Fondo
                    'entrada_opciones': [str, str],
                    'fondo_opciones': [str, str],
                },
                ...
            ],
            'errores': [str],
        }
    """
    logger.info("Iniciando parseo de archivo .eml (%d bytes)", len(contenido_bytes))

    resultado = {
        "asunto": "",
        "año": date.today().year,
        "mes": None,
        "dias": [],
        "errores": [],
    }

    try:
        msg = email.message_from_bytes(contenido_bytes, policy=policy.compat32)
    except Exception as e:
        logger.error("Error al parsear el email: %s", e)
        resultado["errores"].append(f"No se pudo leer el archivo: {e}")
        return resultado

    # Extraer asunto y decodificarlo
    asunto_raw = msg.get("Subject", "")
    from email.header import decode_header
    partes = decode_header(asunto_raw)
    asunto = ""
    for parte, charset in partes:
        if isinstance(parte, bytes):
            asunto += parte.decode(charset or "utf-8", errors="replace")
        else:
            asunto += parte
    resultado["asunto"] = asunto
    logger.info("Asunto del email: %s", asunto)

    # Extraer año y mes del asunto
    resultado["año"] = _extraer_año_del_asunto(asunto)
    meses_rango = _extraer_rango_meses_del_asunto(asunto)
    # "mes" guarda el primer mes del rango (compatibilidad con el resto del código)
    resultado["mes"] = meses_rango[0] if meses_rango else None

    if not resultado["mes"]:
        resultado["errores"].append("No se pudo detectar el mes desde el asunto del email.")
        logger.warning("Mes no detectado en asunto: %s", asunto)
    elif len(meses_rango) > 1:
        logger.info("Plan multi-mes detectado en asunto: meses %s", meses_rango)

    # Extraer y parsear el HTML
    html = _extraer_html(msg)
    if not html:
        resultado["errores"].append("El archivo .eml no contiene contenido HTML.")
        return resultado

    logger.debug("HTML extraído: %d caracteres", len(html))

    parser = FormResponseParser()
    parser.feed(html)
    logger.info("Preguntas detectadas: %d", len(parser.preguntas))

    # Agrupar preguntas por número de día
    dias_dict = {}
    for pregunta in parser.preguntas:
        titulo = pregunta["titulo"]  # e.g. "06 Entrada"
        match = re.match(r"^(\d{2})\s+(Entrada|Fondo)$", titulo)
        if not match:
            continue
        dia_num = int(match.group(1))
        tipo = match.group(2).lower()  # "entrada" o "fondo"

        if dia_num not in dias_dict:
            dias_dict[dia_num] = {
                "dia": dia_num,
                "entrada": None,
                "fondo": None,
                "entrada_opciones": [],
                "fondo_opciones": [],
            }

        dias_dict[dia_num][tipo] = pregunta["seleccionada"]
        dias_dict[dia_num][f"{tipo}_opciones"] = pregunta["opciones"]

        if not pregunta["seleccionada"]:
            logger.warning("Sin selección detectada para: %s", titulo)
            resultado["errores"].append(
                f"No se detectó selección para '{titulo}'. "
                "Puede requerirse edición manual."
            )

    # Construir fechas y ordenar
    # Bug fix: cuando el plan cruza dos meses (ej. "del 29 de Junio al 10 de Julio"),
    # los días del segundo mes tienen números menores que los del primero.
    # Detectamos el salto cuando el número de día decrece respecto al anterior.
    año = resultado["año"]
    mes_inicial = resultado["mes"]
    dias_ordenados = []

    if mes_inicial:
        dias_nums_ordenados = sorted(dias_dict.keys())
        # Determinar qué mes corresponde a cada día:
        # Si hay múltiples meses en el asunto, avanzamos al siguiente mes
        # cuando el número de día "retrocede" (salto de mes).
        mes_actual = mes_inicial
        año_actual = año
        dia_num_anterior = None

        for dia_num in dias_nums_ordenados:
            info = dias_dict[dia_num]

            # Detectar salto al mes siguiente: el día actual es menor que el anterior
            if dia_num_anterior is not None and dia_num < dia_num_anterior:
                mes_actual += 1
                if mes_actual > 12:
                    mes_actual = 1
                    año_actual += 1

            try:
                fecha = date(año_actual, mes_actual, dia_num)
                info["fecha"] = fecha
            except ValueError:
                logger.error("Fecha inválida: %d/%d/%d", dia_num, mes_actual, año_actual)
                resultado["errores"].append(
                    f"Fecha inválida: día {dia_num}, mes {mes_actual}, año {año_actual}"
                )
                info["fecha"] = None

            dia_num_anterior = dia_num
            dias_ordenados.append(info)
    else:
        for dia_num in sorted(dias_dict.keys()):
            info = dias_dict[dia_num]
            info["fecha"] = None
            dias_ordenados.append(info)

    resultado["dias"] = dias_ordenados
    logger.info(
        "Parseo completado: %d días extraídos, %d errores",
        len(dias_ordenados), len(resultado["errores"]),
    )
    return resultado