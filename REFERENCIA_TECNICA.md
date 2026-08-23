# Referencia técnica — diet-service-control

Mapa de funcionalidades → código, para saber rápido qué archivos tocar al
modificar algo. Proyecto Django 5.2 (apps modulares, templates Jinja2,
PostgreSQL). No usa `django.contrib.auth`: la autenticación es propia
(sesión + tabla `Credencial`).

## Índice de apps

| App | Responsabilidad |
|---|---|
| `apps/core` | Modelos compartidos, decorador de autenticación, utilidades de fecha/estado |
| `apps/auth_app` | Login, logout, recuperación y cambio de contraseña |
| `apps/dashboard` | Resumen general (saldos, pendientes) y lista de pedidos siguientes |
| `apps/mes` | Vista calendario mensual (lun-vie) |
| `apps/semana` | Vista semanal de estado de pedidos/entregas |
| `apps/dia` | Ver/editar un día puntual (pedido + entrega), autocompletado de platos |
| `apps/pagos` | Registro y edición de pagos, apertura/cierre de ciclos de pago |
| `apps/reportes` | Reporte de entregas por ciclo de pago + exportación Excel |
| `apps/log` | Muestra el changelog (`changelog/log.md`) en pantalla |
| `apps/importar` | Importa el plan de menú desde el `.eml` de dietservice.pe |

Cada app sigue el mismo patrón: `views.py` (lógica), `urls.py` (rutas),
`apps.py` (config Django). Los templates viven todos juntos en `/templates`
(no por app), y usan Jinja2 (no el motor de templates nativo de Django).

---

## 1. Autenticación y sesión

- **Módulo:** `apps/auth_app/views.py`
- **Modelo:** `Credencial` (`apps/core/models.py`)
- **Decorador:** `protegido` en `apps/core/decorators.py` — envuelve toda
  vista que requiera sesión iniciada; redirige a `login` o a
  `cambiar_clave` si la clave es temporal.
- **Funciones clave:**
  - `credencial_valida(usuario, clave)` — valida contra BD, con fallback a
    `APP_USER`/`APP_PASSWORD` (variables de entorno).
  - `login`, `logout`, `recuperar`, `cambiar_clave`.
- **Templates:** `login.html`, `recuperar.html`, `cambiar_clave.html`.
- **Tocar esto si:** cambia la lógica de login, se agrega roles/permisos,
  o se migra a `django.contrib.auth`.

## 2. Dashboard (resumen general)

- **Módulo:** `apps/dashboard/views.py` → `dashboard()`, `pedidos_siguientes()`
- **Modelos usados:** `Pedido`, `Entrega`, `Pago`, `CicloPago`
- **Utilidades:** `normalizar_fecha`, `formatear_fecha_con_dia` (`apps/core/utils.py`)
- **Templates:** `dashboard.html`, `pedidos_siguientes.html`
- **Qué calcula:** saldo de almuerzos/cenas pagados vs. entregados desde el
  inicio del ciclo activo, y listas de pendientes/por-validar.
- **Tocar esto si:** cambia la fórmula de saldo, o qué cuenta como "pendiente".

## 3. Vista mensual (calendario)

- **Módulo:** `apps/mes/views.py` → `vista_mensual()`, `_estado_color()`
- **Modelos usados:** `CicloPago`, `Pedido`, `Entrega`
- **Templates:** `mes.html`
- **Constantes:** `MESES_ES`, `CABECERA_SEMANA` (mismo archivo)
- **Tocar esto si:** cambia el layout del calendario o los colores de estado
  (`light`/`success`/`danger`/`warning`).

## 4. Vista semanal

- **Módulo:** `apps/semana/views.py` → `vista_semanal()`
- **Utilidades:** `obtener_fechas_semana`, `estado_textual` (`apps/core/utils.py`)
- **Templates:** `semana.html`
- **Tocar esto si:** cambia qué días se muestran (hoy son solo lun-vie) o el
  texto descriptivo de estado (`estado_textual`).

## 5. Edición de un día puntual

- **Módulo:** `apps/dia/views.py`
- **Modelos usados:** `Pedido`, `Entrega`
- **Funciones clave:**
  - `cargar_datos_dia(fecha_form)` — arma el contexto completo de un día
    (pedido + entrega + navegación a día anterior/siguiente hábil).
  - `siguiente_dia_habil` / `anterior_dia_habil` — saltan fines de semana.
  - `ver_dia` (solo lectura) vs `editar_dia` (GET muestra form, POST guarda).
  - `sugerencias_plato` — endpoint JSON de autocompletado, usa
    `buscar_platos_similares` (`apps/core/utils.py`).
- **Templates:** `editar_dia.html`
- **Tocar esto si:** cambia qué campos tiene un pedido/entrega, o el
  autocompletado de platos.

## 6. Pagos y ciclos de pago

- **Módulo:** `apps/pagos/views.py` → `pagos()`, `editar_pago()`
- **Modelos usados:** `Pago`, `CicloPago`, `Pedido`, `Log`
- **Utilidades:** `formatear_fecha`, `ciclo_agotado` (`apps/core/utils.py`)
- **Lógica central:** al registrar un pago, si no hay ciclo abierto se crea
  uno; si el ciclo abierto ya se agotó (`ciclo_agotado`) se cierra y se abre
  uno nuevo; si aún no se agotó, el pago queda "pendiente" (sin ciclo).
- **Funciones de soporte (`apps/core/utils.py`):**
  `contar_entregas_ciclo(ciclo)`, `ciclo_agotado(ciclo)`.
- **Templates:** `pagos.html`, `editar_pago.html`
- **Tocar esto si:** cambia la regla de apertura/cierre de ciclos, o qué
  cuenta como "entrega" dentro de un ciclo.

## 7. Reportes y exportación a Excel

- **Módulo:** `apps/reportes/views.py` → `reporte_ciclo()`, `ciclo_excel()`
- **Dependencia:** `pandas` + `xlsxwriter` (formato condicional en el Excel)
- **Modelos usados:** `Entrega`, `Pago`, `CicloPago`
- **Templates:** `reporte_ciclo.html`
- **Tocar esto si:** cambia el contenido/formato del Excel exportado o los
  filtros del reporte en pantalla.

## 8. Changelog en pantalla

- **Módulo:** `apps/log/views.py` → `log()`
- **Fuente de datos:** archivo `changelog/log.md` (texto plano, no modelo)
- **Templates:** `log.html`
- **Tocar esto si:** cambia el formato del changelog o su fuente (hoy lee
  directo del archivo `.md`, no de la tabla `Log`).

## 9. Importación del plan de menú (.eml)

- **Módulo:** `apps/importar/parser.py` (parseo) + `apps/importar/views.py` (flujo web)
- **Modelo usado:** `Pedido` (`update_or_create` por fecha)
- **Formato de entrada:** correo "Tu pedido de menú quedó registrado" de
  `notificacion@dietservice.pe` — tabla HTML con fecha ISO explícita por
  día y filas Entrada/Fondo/Cena.
- **Clases/funciones clave (`parser.py`):**
  - `PedidoMenuParser` (subclase de `HTMLParser`) — recorre la tabla y arma
    `filas` (lista de `{fecha_texto, tipo, plato}`) + `nombre` del cliente.
  - `_extraer_html(msg)`, `_decodificar_asunto(msg)` — helpers de parseo del `.eml`.
  - `parsear_eml(contenido_bytes)` — función pública, agrupa filas por
    fecha (arrastrando la fecha cuando la celda viene vacía) y devuelve
    `{asunto, nombre, dias, errores}`.
- **Vistas (`views.py`):** `importar_eml` (GET form / POST preview),
  `confirmar_importacion` (POST guarda en BD, incluye `cena`/`plato_cena`).
- **Templates:** `importar.html`, `importar_preview.html`
- **Tocar esto si:** dietservice.pe vuelve a cambiar el formato del correo,
  o se quiere soportar otro origen de importación (ver nota abajo).
- **Nota:** el parser de Google Forms (formato anterior) fue eliminado por
  completo; no hay compatibilidad retroactiva con ese `.eml`.

---

## Modelos de datos (`apps/core/models.py`)

| Modelo | Tabla | Campos clave | Notas |
|---|---|---|---|
| `Credencial` | `credenciales` | `usuario`, `contrasena` | columna BD `contraseña` |
| `Pedido` | `pedidos` | `fecha` (PK), `almuerzo`, `cena`, `entrada`, `fondo`, `plato_cena`, `feriado`, `observaciones` | `almuerzo`/`cena` son flags 1/0, no booleanos |
| `Entrega` | `entregas` | `fecha`, `entregado_almuerzo`, `entregado_cena`, `observaciones` | no tiene PK sobre `fecha` (puede haber más de una fila histórica) |
| `CicloPago` | `ciclos_pago` | `tipo`, `fecha_inicio`, `fecha_fin` | `fecha_fin` null = ciclo abierto |
| `Pago` | `pagos` | `fecha`, `tipo`, `monto`, `cantidad`, `ciclo` (FK) | `ciclo` puede ser null (pago "pendiente") |
| `Log` | `log` | `timestamp`, `accion`, `detalle` | solo se usa desde `apps/pagos`; el changelog visible (`apps/log`) lee el `.md`, no esta tabla |

## Utilidades transversales (`apps/core/utils.py`)

| Función | Uso |
|---|---|
| `obtener_fechas_semana` | arma fechas lun-vie de una semana ISO |
| `normalizar_fecha` | castea `str`/`datetime`/`date` a `date` |
| `normalizar_fecha_ddmmaaaa` | parsea `DD-MM-YYYY` |
| `formatear_fecha` / `formatear_fecha_con_dia` | formato de salida para templates |
| `estado_textual` | texto de estado de un día (dashboard/semana) |
| `buscar_platos_similares` | autocompletado en `apps/dia` |
| `contar_entregas_ciclo` / `ciclo_agotado` | lógica de ciclos en `apps/pagos` |

## Configuración del proyecto

| Archivo | Contenido |
|---|---|
| `diet_service_control/settings.py` | apps instaladas, BD (Postgres), logging, credenciales por entorno (`APP_USER`/`APP_PASSWORD`) |
| `diet_service_control/urls.py` | registro de rutas raíz (`include` de cada app) + iconos apple-touch |
| `diet_service_control/jinja2.py` | entorno Jinja2 custom: `url_for_django` (mapea `modulo.vista` → nombre de URL Django) y `CsrfExtension` (`{% csrf_token %}` en Jinja2) |

**Importante:** si se agrega una vista nueva con `url_for(...)` en un
template, hay que sumar la entrada correspondiente en `endpoint_map` dentro
de `diet_service_control/jinja2.py`, o el `url_for` fallará en runtime.

---

## Guía rápida: "quiero cambiar X, ¿qué toco?"

| Quiero... | Archivos a revisar |
|---|---|
| Cambiar el login o las credenciales | `apps/auth_app/views.py`, `apps/core/models.py` (`Credencial`) |
| Cambiar qué se considera "pendiente" en el dashboard | `apps/dashboard/views.py` |
| Cambiar colores/estados del calendario mensual | `apps/mes/views.py` (`_estado_color`) |
| Agregar un campo nuevo a un pedido/entrega | `apps/core/models.py`, `apps/dia/views.py` (`cargar_datos_dia`, `editar_dia`), `templates/editar_dia.html`, migración en `apps/core/migrations/` |
| Cambiar la regla de apertura/cierre de ciclos de pago | `apps/pagos/views.py`, `apps/core/utils.py` (`ciclo_agotado`) |
| Cambiar el Excel exportado | `apps/reportes/views.py` (`ciclo_excel`) |
| Cambiar el formato de importación del menú | `apps/importar/parser.py`, `apps/importar/views.py`, `templates/importar*.html` |
| Agregar una vista/URL nueva | crear en la app correspondiente, registrar en su `urls.py`, incluir en `diet_service_control/urls.py`, y sumar a `endpoint_map` en `jinja2.py` si el template usa `url_for` |
