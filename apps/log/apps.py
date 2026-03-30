from django.apps import AppConfig


class LogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.log"
    label = "log_app"
    verbose_name = "Registro"
