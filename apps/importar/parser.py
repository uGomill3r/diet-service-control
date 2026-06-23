"""
Parser del archivo .eml generado por Google Forms al completar el formulario
de Plan de Alimentacion.

Estructura del email:
- Parte text/plain (base64): lista plana de opciones por dia, la seleccionada
  aparece PRIMERO en cada bloque.
- Parte text/html: tiene aria-checked="true" en la opcion elegida.

Usamos el HTML porque es mas confiable para identificar la seleccion.
"""
import email
import logging
import re
from datetime import date
from email import policy
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

# Mapeo de nombres de mes en espanol a numero
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

        # Detectar h2 que es titulo de pregunta
        if tag == "h2":
            self._capturando_titulo = True
            self._titulo_buffer = ""

        # Detectar div[role=radio] — cada opcion de respuesta
        if tag == "div" and attrs_dict.get("role") == "radio":
            self._opcion_checked = attrs_dict.get("aria-checked") == "true"
            self._opcion_buffer = ""
            self._dentro_td_opcion = False

        # El texto de la opcion esta en el <td> que sigue al div radio
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


def _extraer_anno_del_asunto(asunto):
    """Intenta extraer el anno desde el asunto del email."""
    match = re.search(r"\b(20\d{2})\b", asunto)
    if match:
        return int(match.group(1))
    return date.today().year


def _extraer_mes_del_asunto(asunto):
    """Extrae el numero de mes desde el asunto del email.

    Retorna el primer mes encontrado por posicion en el texto.
    Para planes que cruzan meses, usar _extraer_rango_meses_del_asunto.
    """
    return (_extraer_rango_meses_del_asunto(asunto) or [None])[0]


def _extraer_rango_meses_del_asunto(asunto):
    """Extrae todos los meses mencionados en el asunto, en el orden en que aparecen.

    Retorna una lista de numeros de mes segun su posicion en el texto.
    Ejemplo: "del 29 de Junio al 10 de Julio" -> [6, 7]
    """
    asunto_lower = asunto.lower()
    encontrados = []
    for nombre, numero in MESES.items():
        pos = asunto_lower.find(nombre)
        if pos != -1:
            encontrados.append((pos, numero))
    encontrados.sort()
    return [numero for _, numero in encontrados]


def _extraer_dia_inicio_del_asunto(asunto):
    """Extrae el primer numero de dia mencionado en el asunto.

    Ejemplo: "del 29 de Junio al 10 de Julio" -> 29
    """
    match = re.search(r"\b(\d{1,2})\s+de\s+\w+", asunto, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def parsear_eml(contenido_bytes):
    """
    Parsea el contenido binario de un archivo .eml y extrae los platos
    seleccionados por dia.

    Retorna:
        {
            'asunto': str,
            'anno': int,
            'mes': int,
            'dias': [
                {
                    'dia': int,           # numero de dia del mes
                    'fecha': date,
                    'entrada': str,       # opcion seleccionada para Entrada
                    'fondo': str,         # opcion seleccionada para Fondo
                    'entrada_opciones': [str, str],
                    'fondo_opciones': [str, str],
                },
                ...\
            ],
            'errores': [str],
        }
    """
    logger.info("Iniciando parseo de archivo .eml (%d bytes)", len(contenido_bytes))

    resultado = {
        "asunto": "",
        "anno": date.today().year,
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

    # Extraer anno y meses del asunto
    anno = _extraer_anno_del_asunto(asunto)
    resultado["anno"] = anno
    # Alias para compatibilidad con templates que usen "año"
    resultado["año"] = anno

    meses_rango = _extraer_rango_meses_del_asunto(asunto)
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

    logger.debug("HTML extraido: %d caracteres", len(html))

    parser = FormResponseParser()
    parser.feed(html)
    logger.info("Preguntas detectadas: %d", len(parser.preguntas))

    # Agrupar preguntas por numero de dia
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
            logger.warning("Sin seleccion detectada para: %s", titulo)
            resultado["errores"].append(
                f"No se detecto seleccion para '{titulo}'. "
                "Puede requerirse edicion manual."
            )

    # Construir fechas y ordenar
    #
    # Fix bug multi-mes: cuando el plan cruza dos meses (ej. "del 29 de Junio
    # al 10 de Julio"), los dias del primer mes tienen numeros ALTOS (29, 30)
    # y los del segundo mes tienen numeros BAJOS (1..10).
    # Ordenar numericamente pone los dias bajos primero, haciendo imposible
    # detectar el salto por "retroceso".
    #
    # Solucion: extraer el dia de inicio del asunto (ej. 29) como umbral.
    # - dias >= dia_inicio  →  primer mes del rango
    # - dias <  dia_inicio  →  segundo mes del rango
    # Si el asunto no tiene rango (un solo mes), se asigna ese mes a todos.

    mes_inicial = resultado["mes"]
    dias_ordenados = []

    if mes_inicial:
        dia_inicio = _extraer_dia_inicio_del_asunto(asunto) if len(meses_rango) > 1 else None

        for dia_num in sorted(dias_dict.keys()):
            info = dias_dict[dia_num]

            if dia_inicio is not None and len(meses_rango) > 1:
                # Plan multi-mes: usar umbral para asignar mes correcto
                if dia_num >= dia_inicio:
                    mes_actual = meses_rango[0]
                    anno_actual = anno
                else:
                    mes_actual = meses_rango[1]
                    anno_actual = anno
                    # Manejar rollover de anno (ej. diciembre -> enero)
                    if meses_rango[1] < meses_rango[0]:
                        anno_actual = anno + 1
            else:
                # Plan de un solo mes
                mes_actual = mes_inicial
                anno_actual = anno

            try:
                fecha = date(anno_actual, mes_actual, dia_num)
                info["fecha"] = fecha
            except ValueError:
                logger.error("Fecha invalida: %d/%d/%d", dia_num, mes_actual, anno_actual)
                resultado["errores"].append(
                    f"Fecha invalida: dia {dia_num}, mes {mes_actual}, anno {anno_actual}"
                )
                info["fecha"] = None

            dias_ordenados.append(info)
    else:
        for dia_num in sorted(dias_dict.keys()):
            info = dias_dict[dia_num]
            info["fecha"] = None
            dias_ordenados.append(info)

    # Ordenar cronologicamente por fecha real
    dias_ordenados.sort(key=lambda d: d["fecha"] if d["fecha"] else date.max)

    resultado["dias"] = dias_ordenados
    logger.info(
        "Parseo completado: %d dias extraidos, %d errores",
        len(dias_ordenados), len(resultado["errores"]),
    )
    return resultado