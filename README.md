# Diet Service Control

Aplicación web interna para llevar el control de pedidos, entregas y pagos
del servicio de almuerzos/cenas de **Diet Service**. Permite ver el estado
día a día y por semana, registrar pagos por ciclos, generar reportes en
Excel, e importar automáticamente el plan de menú desde el correo de
confirmación de pedido.

Migrado desde una app Flask original a **Django 5.2**, manteniendo la
misma base de datos y lógica de negocio.

## Stack

- **Backend:** Django 5.2 (sin `django.contrib.auth`; autenticación propia por sesión)
- **Templates:** Jinja2 (no el motor nativo de Django — ver `diet_service_control/jinja2.py`)
- **Base de datos:** PostgreSQL 17
- **Servidor WSGI:** Gunicorn
- **Estáticos en producción:** WhiteNoise
- **Reportes:** pandas + XlsxWriter
- **Despliegue:** Docker Compose (local) / Render (producción)

## Estructura del proyecto

```
diet_service_control/     Configuración del proyecto (settings, urls, jinja2, wsgi)
apps/
  core/                    Modelos compartidos, decorador de autenticación, utilidades
  auth_app/                Login, logout, recuperación y cambio de contraseña
  dashboard/                Resumen general y pedidos pendientes
  mes/                      Vista calendario mensual
  semana/                   Vista semanal de estado de pedidos/entregas
  dia/                      Ver/editar un día puntual
  pagos/                    Registro de pagos y ciclos de pago
  reportes/                 Reportes por ciclo + exportación a Excel
  log/                      Muestra el changelog en pantalla
  importar/                 Importación del plan de menú desde .eml
templates/                 Templates Jinja2 (compartidos entre apps)
static/                    CSS, JS e íconos
changelog/log.md            Registro editorial de acciones (texto plano)
```

Para el detalle de qué módulo/función tocar según la funcionalidad a
modificar, ver **`REFERENCIA_TECNICA.md`**.

## Requisitos

- Docker y Docker Compose (recomendado), **o**
- Python 3.12 + PostgreSQL 17 instalados localmente

## Configuración

Crear un archivo `.env` en la raíz del proyecto (no versionado) con:

```env
SECRET_KEY=una-clave-secreta-larga-y-unica
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=diet_service_control
DB_USER=postgres
DB_PASSWORD=postgres

APP_USER=admin
APP_PASSWORD=cambia-esta-clave
```

`APP_USER`/`APP_PASSWORD` son la credencial de acceso inicial a la app; una
vez logueado se puede cambiar la contraseña desde la propia interfaz
(queda guardada en la tabla `credenciales`, con estas variables como
respaldo/fallback).

## Levantar el proyecto con Docker Compose

```bash
docker compose up --build
```

Esto levanta la base de datos PostgreSQL, corre las migraciones, junta los
estáticos y sirve la app con Gunicorn en `http://localhost:8000` (puerto
configurable con `WEB_PORT`).

## Levantar el proyecto sin Docker

```bash
python -m venv venv
source venv/bin/activate          # en Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```

Requiere una instancia de PostgreSQL corriendo y accesible con las
variables `DB_*` del `.env`.

## Funcionalidades principales

- **Dashboard:** saldo de almuerzos/cenas pagados vs. entregados desde el
  inicio del ciclo activo, y listado de pendientes.
- **Vistas mensual y semanal:** estado visual (entregado / pendiente / no
  entregado) de cada día hábil.
- **Edición de día:** pedido (entrada, fondo, cena) y entrega de una fecha
  puntual, con autocompletado de platos ya usados.
- **Pagos y ciclos:** registro de pagos, apertura/cierre automático de
  ciclos según el paquete contratado se agote.
- **Reportes:** listado de entregas por ciclo de pago, exportable a Excel.
- **Importación de menú:** sube el `.eml` del correo "Tu pedido de menú
  quedó registrado" de dietservice.pe y carga automáticamente entrada,
  fondo y cena de cada día en el rango del pedido.
- **Changelog:** vista de solo lectura del archivo `changelog/log.md`.

## Logging

El proyecto registra logs por nivel (`INFO` para resultados de operaciones
importantes, `WARNING`/`ERROR` en validaciones y bloques `except`,
`DEBUG` para detalle interno) en cada app bajo el logger `apps`. En
desarrollo se ven en consola; en producción quedan en el log del proceso
Gunicorn/Render.

## Despliegue en Render

La imagen se construye con el `Dockerfile` incluido. Render inyecta
automáticamente la variable `RENDER=true`, que la app usa para activar
WhiteNoise y el almacenamiento comprimido de estáticos
(`diet_service_control/settings.py`, flag `IS_RENDER`).

## Documentación relacionada

- `REFERENCIA_TECNICA.md` — mapa de funcionalidades a módulos/clases/funciones,
  útil antes de modificar cualquier parte del código.
- `changelog/log.md` — registro histórico de acciones del sistema.
