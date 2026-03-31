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
from apps.core.utils import formatear_fecha, ciclo_agotado

logger = logging.getLogger(__name__)


@protegido
def pagos(request):
    """Lista de pagos y formulario para registrar uno nuevo."""
    aviso = None

    if request.method == "POST":
        fecha_iso = request.POST.get("fecha")
        tipo = request.POST.get("tipo")
        monto = float(request.POST.get("monto", 0))
        cantidad = int(request.POST.get("cantidad", 0))

        logger.info("Registrando pago — fecha: %s, tipo: %s, cantidad: %d", fecha_iso, tipo, cantidad)

        # Buscar ciclo abierto para el tipo
        ciclo_activo = (
            CicloPago.objects.filter(tipo=tipo, fecha_fin__isnull=True)
            .order_by("-fecha_inicio")
            .first()
        )

        ciclo_para_pago = None

        if ciclo_activo is None:
            # No hay ciclo abierto — crear uno nuevo directamente
            ciclo_para_pago = CicloPago.objects.create(tipo=tipo, fecha_inicio=fecha_iso)
            logger.info(
                "Sin ciclo activo para '%s' — nuevo ciclo creado id=%d",
                tipo, ciclo_para_pago.id,
            )
        elif ciclo_agotado(ciclo_activo):
            # El paquete anterior se agotó — cerrar y abrir nuevo ciclo
            ultimo_pedido = (
                Pedido.objects.filter(
                    **{f"{tipo}__gt": 0},
                    fecha__gte=ciclo_activo.fecha_inicio,
                    fecha__lt=fecha_iso,
                )
                .order_by("-fecha")
                .values_list("fecha", flat=True)
                .first()
            )
            ciclo_activo.fecha_fin = ultimo_pedido or fecha_iso
            ciclo_activo.save()
            logger.info(
                "Ciclo id=%d agotado — cerrado con fecha_fin: %s",
                ciclo_activo.id, ciclo_activo.fecha_fin,
            )
            ciclo_para_pago = CicloPago.objects.create(tipo=tipo, fecha_inicio=fecha_iso)
            logger.info("Nuevo ciclo creado id=%d", ciclo_para_pago.id)
        else:
            # Paquete anterior aún no agotado — registrar pago sin ciclo (pendiente)
            ciclo_para_pago = None
            aviso = (
                f"El paquete de {tipo} actual todavía no se agotó. "
                "El pago fue registrado sin ciclo asignado (pendiente)."
            )
            logger.warning(
                "Pago registrado sin ciclo — ciclo activo id=%d aún no agotado",
                ciclo_activo.id,
            )

        # Registrar el pago (ciclo puede ser None si está pendiente)
        nuevo_pago = Pago.objects.create(
            fecha=fecha_iso,
            tipo=tipo,
            monto=monto,
            cantidad=cantidad,
            ciclo=ciclo_para_pago,
        )

        Log.objects.create(
            timestamp=timezone.now(),
            accion="Pago registrado",
            detalle=(
                f"{fecha_iso} | {tipo} x {monto} "
                f"(ciclo {ciclo_para_pago.id if ciclo_para_pago else 'pendiente'})"
            ),
        )
        logger.info(
            "Pago registrado — id: %d, ciclo: %s",
            nuevo_pago.id,
            ciclo_para_pago.id if ciclo_para_pago else "pendiente",
        )

        # Redirigir con aviso en sesión si corresponde
        if aviso:
            request.session["aviso_pagos"] = aviso
        return redirect(reverse("pagos"))

    # GET — recuperar aviso de sesión si lo hay
    aviso = request.session.pop("aviso_pagos", None)

    # Listar pagos
    pagos_qs = (
        Pago.objects.select_related("ciclo")
        .order_by("-fecha")
        .values_list("id", "fecha", "tipo", "monto", "cantidad", "ciclo__fecha_inicio")
    )
    pagos_list = [
        (
            p[0],
            formatear_fecha(p[1]),
            p[2],
            p[3],
            p[4],
            formatear_fecha(p[5]) if p[5] else "—",
        )
        for p in pagos_qs
    ]

    totales = {
        row["tipo"]: row["total"]
        for row in Pago.objects.values("tipo").annotate(total=Sum("monto"))
    }

    logger.debug("Listando %d pagos", len(pagos_list))
    return render(request, "pagos.html", {"pagos": pagos_list, "totales": totales, "aviso": aviso})


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
        nuevo_ciclo_id = request.POST.get("ciclo_id") or None

        fecha_original = pago_obj.fecha
        tipo_original = pago_obj.tipo

        logger.info(
            "Editando pago id=%d — de %s/%s a %s/%s",
            id, fecha_original, tipo_original, nueva_fecha, nuevo_tipo,
        )

        # Asignar ciclo manualmente si se seleccionó uno, o dejar None
        ciclo_nuevo = None
        if nuevo_ciclo_id:
            try:
                ciclo_nuevo = CicloPago.objects.get(id=nuevo_ciclo_id)
                logger.info("Ciclo asignado manualmente — id=%d", ciclo_nuevo.id)
            except CicloPago.DoesNotExist:
                logger.warning("Ciclo id=%s no encontrado al editar pago id=%d", nuevo_ciclo_id, id)

        pago_obj.fecha = nueva_fecha
        pago_obj.tipo = nuevo_tipo
        pago_obj.monto = nuevo_monto
        pago_obj.cantidad = nueva_cantidad
        pago_obj.ciclo = ciclo_nuevo
        pago_obj.save()

        Log.objects.create(
            timestamp=timezone.now(),
            accion="Pago editado",
            detalle=(
                f"Editado pago {id}: {nueva_fecha} | {nuevo_tipo} x {nuevo_monto} "
                f"(ciclo {ciclo_nuevo.id if ciclo_nuevo else 'pendiente'})"
            ),
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