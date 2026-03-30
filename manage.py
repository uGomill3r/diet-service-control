#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Carga variables del .env para desarrollo local
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # En producción/Docker las variables vienen del entorno directamente

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "diet_service_control.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Verifica que esté instalado y "
            "que el entorno virtual esté activado."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()