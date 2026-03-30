"""
Migración inicial que replica el esquema de tablas del proyecto Flask original.
Tablas: credenciales, pedidos, entregas, ciclos_pago, pagos, log
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Credencial",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("usuario", models.CharField(max_length=50, unique=True)),
                ("contrasena", models.CharField(db_column="contraseña", max_length=100)),
                ("actualizado", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "credenciales"},
        ),
        migrations.CreateModel(
            name="Pedido",
            fields=[
                ("fecha", models.DateField(primary_key=True, serialize=False)),
                ("semana", models.IntegerField(blank=True, null=True)),
                ("almuerzo", models.IntegerField(default=1)),
                ("cena", models.IntegerField(blank=True, null=True)),
                ("feriado", models.BooleanField(default=False)),
                ("entrada", models.TextField(blank=True, null=True)),
                ("fondo", models.TextField(blank=True, null=True)),
                ("plato_cena", models.TextField(blank=True, null=True)),
                ("observaciones", models.TextField(blank=True, null=True)),
            ],
            options={"db_table": "pedidos"},
        ),
        migrations.CreateModel(
            name="Entrega",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("fecha", models.DateField()),
                ("entregado_almuerzo", models.IntegerField(blank=True, null=True)),
                ("entregado_cena", models.IntegerField(blank=True, null=True)),
                ("observaciones", models.TextField(blank=True, null=True)),
            ],
            options={"db_table": "entregas"},
        ),
        migrations.CreateModel(
            name="CicloPago",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("tipo", models.CharField(max_length=20)),
                ("fecha_inicio", models.DateField()),
                ("fecha_fin", models.DateField(blank=True, null=True)),
            ],
            options={"db_table": "ciclos_pago"},
        ),
        migrations.CreateModel(
            name="Pago",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("fecha", models.DateField()),
                ("tipo", models.CharField(max_length=20)),
                ("monto", models.FloatField()),
                ("cantidad", models.IntegerField()),
                (
                    "ciclo",
                    models.ForeignKey(
                        blank=True,
                        db_column="ciclo_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pagos",
                        to="core.ciclopago",
                    ),
                ),
            ],
            options={"db_table": "pagos"},
        ),
        migrations.CreateModel(
            name="Log",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("timestamp", models.DateTimeField()),
                ("accion", models.CharField(max_length=100)),
                ("detalle", models.TextField(blank=True, null=True)),
            ],
            options={"db_table": "log"},
        ),
    ]
