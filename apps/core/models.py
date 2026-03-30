"""
Modelos Django equivalentes a los modelos SQLAlchemy del proyecto Flask.
Tablas: credenciales, pedidos, entregas, pagos, ciclos_pago, log
"""
import logging
from django.db import models

logger = logging.getLogger(__name__)


class Credencial(models.Model):
    """Almacena credenciales de acceso de los usuarios."""

    usuario = models.CharField(max_length=50, unique=True)
    contrasena = models.CharField(
        max_length=100,
        db_column="contraseña",  # Mantiene nombre de columna original
    )
    actualizado = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "credenciales"

    def __str__(self):
        return f"<Credencial {self.usuario}>"


class Pedido(models.Model):
    """Representa un pedido de comida para una fecha específica."""

    fecha = models.DateField(primary_key=True)
    semana = models.IntegerField(null=True, blank=True)
    almuerzo = models.IntegerField(default=1)
    cena = models.IntegerField(null=True, blank=True)
    feriado = models.BooleanField(default=False)
    entrada = models.TextField(null=True, blank=True)
    fondo = models.TextField(null=True, blank=True)
    plato_cena = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "pedidos"

    def __str__(self):
        return f"<Pedido {self.fecha} | Almuerzo: {self.almuerzo}, Cena: {self.cena}>"


class Entrega(models.Model):
    """Registra las entregas realizadas para un pedido."""

    fecha = models.DateField()
    entregado_almuerzo = models.IntegerField(null=True, blank=True)
    entregado_cena = models.IntegerField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "entregas"

    def __str__(self):
        return f"<Entrega {self.fecha} | Almuerzo: {self.entregado_almuerzo}, Cena: {self.entregado_cena}>"


class CicloPago(models.Model):
    """Define un ciclo de pago para un tipo de comida."""

    tipo = models.CharField(max_length=20)  # 'almuerzo' o 'cena'
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "ciclos_pago"

    def __str__(self):
        return f"<CicloPago {self.tipo} desde {self.fecha_inicio}>"


class Pago(models.Model):
    """Registra un pago asociado a un ciclo de pago."""

    fecha = models.DateField()
    tipo = models.CharField(max_length=20)
    monto = models.FloatField()
    cantidad = models.IntegerField()
    ciclo = models.ForeignKey(
        CicloPago,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="ciclo_id",
        related_name="pagos",
    )

    class Meta:
        db_table = "pagos"

    def __str__(self):
        return f"<Pago {self.fecha} | {self.tipo} x {self.monto}>"


class Log(models.Model):
    """Registro de acciones importantes del sistema."""

    timestamp = models.DateTimeField()
    accion = models.CharField(max_length=100)
    detalle = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "log"

    def __str__(self):
        return f"<Log {self.timestamp} | {self.accion}>"
