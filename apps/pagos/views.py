"""
Vistas de registro y edición de pagos y ciclos de pago.
Migrado desde blueprints/pagos.py de Flask.
"""
import logging
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum
from apps.core.decorators import protegido
from apps.core.models import Pago, CicloPago, Pedido, Log
from apps.core.utils import formatear_fecha

logger = logging.getLogger(__name__)


@protegido
def pagos(request):
    """Lista de pagos y formulario para registrar uno nuevo."""
    if request.method == "POST":
        fecha_iso = request.POST.get("fecha")
        tipo = request.POST.get("tipo")
        monto = float(request.POST.get("monto", 0))
        cantidad = int(request.POST.get("cantidad", 0))

        logger.info("Registrando pago — fecha: %s, tipo: %s, cantidad: %d", fecha_iso, tipo, cantidad)

        # Verificar si hay ciclo abierto para el tipo
        ciclo_abierto = (
            CicloPago.objects.filter(tipo=tipo, fecha_fin__isnull=True)
            .order_by("-fecha_inicio")
            .first()
        )

        if ciclo_abierto and fecha_iso > ciclo_abierto.fecha_inicio.isoformat():
            # Cerrar ciclo anterior buscando el último pedido del tipo
            campo_filter = {f"{tipo}__gt": 0, "fecha__gte": ciclo_abierto.fecha_inicio, "fecha__lt": fecha_iso}
            ultimo_pedido = (
                Pedido.objects.filter(**campo_filter)
                .order_by("-fecha")
                .values_list("fecha", flat=True)
                .first()
            )
            ciclo_abierto.fecha_fin = ultimo_pedido or fecha_iso
            ciclo_abierto.save()
            logger.info("Ciclo anterior cerrado — id: %d, fecha_fin: %s", ciclo_abierto.id, ciclo_abierto.fecha_fin)

        # Crear nuevo ciclo
        nuevo_ciclo = CicloPago.objects.create(tipo=tipo, fecha_inicio=fecha_iso)
        logger.debug("Nuevo ciclo creado — id: %d", nuevo_ciclo.id)

        # Registrar pago
        nuevo_pago = Pago.objects.create(
            fecha=fecha_iso,
            tipo=tipo,
            monto=monto,
            cantidad=cantidad,
            ciclo=nuevo_ciclo,
        )

        # Log de la acción
        Log.objects.create(
            timestamp=timezone.now(),
            accion="Pago registrado",
            detalle=f"{fecha_iso} | {tipo} x {monto} (ciclo {nuevo_ciclo.id})",
        )
        logger.info("Pago registrado — id: %d, ciclo: %d", nuevo_pago.id, nuevo_ciclo.id)

        return redirect(reverse("pagos"))

    # GET — listar pagos
    pagos_qs = (
        Pago.objects.select_related("ciclo")
        .order_by("-fecha")
        .values_list("id", "fecha", "tipo", "monto", "ciclo__fecha_inicio")
    )
    pagos_list = [
        (p[0], formatear_fecha(p[1]), p[2], p[3], formatear_fecha(p[4]) if p[4] else "—")
        for p in pagos_qs
    ]

    totales = {
        row["tipo"]: row["total"]
        for row in Pago.objects.values("tipo").annotate(total=Sum("monto"))
    }

    logger.debug("Listando %d pagos", len(pagos_list))
    return render(request, "pagos.html", {"pagos": pagos_list, "totales": totales})


@protegido
def editar_pago(request, id):
    """Edición de un pago existente."""
    pago_obj = get_object_or_404(Pago, id=id)

    ciclos_qs = CicloPago.objects.order_by("-fecha_inicio")
    ciclos = [
        (c.id, f"{c.tipo.capitalize()} desde {formatear_fecha(c.fecha_inicio)}")
        for c in ciclos_qs
    ]

    if request.method == "POST":
        nueva_fecha = request.POST.get("fecha")
        nuevo_tipo = request.POST.get("tipo")
        nuevo_monto = float(request.POST.get("monto", 0))
        nueva_cantidad = int(request.POST.get("cantidad", 0))

        fecha_original = pago_obj.fecha
        tipo_original = pago_obj.tipo
        ciclo_original = pago_obj.ciclo

        logger.info(
            "Editando pago id=%d — de %s/%s a %s/%s",
            id, fecha_original, tipo_original, nueva_fecha, nuevo_tipo,
        )

        # Si tipo o fecha cambian, cerrar ciclo anterior si está abierto
        if (tipo_original != nuevo_tipo or str(fecha_original) != nueva_fecha) and ciclo_original:
            if ciclo_original.fecha_fin is None:
                campo_filter = {f"{tipo_original}__gt": 0}
                ultimo_pedido = (
                    Pedido.objects.filter(**campo_filter)
                    .order_by("-fecha")
                    .values_list("fecha", flat=True)
                    .first()
                )
                ciclo_original.fecha_fin = ultimo_pedido or fecha_original
                ciclo_original.save()
                logger.debug("Ciclo anterior cerrado tras edición — id: %d", ciclo_original.id)

        # Buscar ciclo abierto para el nuevo tipo o crear uno nuevo
        ciclo_nuevo = (
            CicloPago.objects.filter(tipo=nuevo_tipo, fecha_fin__isnull=True)
            .order_by("-fecha_inicio")
            .first()
        )
        if not ciclo_nuevo:
            ciclo_nuevo = CicloPago.objects.create(tipo=nuevo_tipo, fecha_inicio=nueva_fecha)
            logger.debug("Nuevo ciclo creado durante edición — id: %d", ciclo_nuevo.id)

        pago_obj.fecha = nueva_fecha
        pago_obj.tipo = nuevo_tipo
        pago_obj.monto = nuevo_monto
        pago_obj.cantidad = nueva_cantidad
        pago_obj.ciclo = ciclo_nuevo
        pago_obj.save()

        Log.objects.create(
            timestamp=timezone.now(),
            accion="Pago editado",
            detalle=f"Editado pago {id}: {nueva_fecha} | {nuevo_tipo} x {nuevo_monto} (ciclo {ciclo_nuevo.id})",
        )
        logger.info("Pago id=%d actualizado correctamente", id)
        return redirect(reverse("pagos"))

    # GET — mostrar formulario con datos del pago
    pago_data = (
        pago_obj.fecha,
        pago_obj.tipo,
        pago_obj.monto,
        pago_obj.cantidad,
        pago_obj.ciclo_id,
    )
    return render(
        request,
        "editar_pago.html",
        {"pago": pago_data, "pago_id": id, "ciclos": ciclos},
    )
