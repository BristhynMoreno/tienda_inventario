from decimal import Decimal

from django.db import transaction

from .models import DetalleVenta, Producto, Venta


class VentaError(Exception):
    """Error de negocio al registrar una venta (se muestra al usuario)."""


def registrar_venta(vendedor, cliente, items):
    """Crea una venta con sus detalles y descuenta el stock de forma atómica.

    items: lista de {"producto_id": int, "cantidad": int}.
    """
    cantidades = {}
    for item in items:
        try:
            pid = int(item["producto_id"])
            cantidad = int(item["cantidad"])
        except (KeyError, TypeError, ValueError):
            raise VentaError("Datos de producto inválidos.")
        if cantidad < 1:
            raise VentaError("La cantidad debe ser al menos 1.")
        cantidades[pid] = cantidades.get(pid, 0) + cantidad
    if not cantidades:
        raise VentaError("El carrito está vacío.")

    with transaction.atomic():
        # Bloqueo de filas (en orden fijo) para no vender stock que otro usuario ya vendió.
        productos = (
            Producto.objects.select_for_update()
            .filter(pk__in=cantidades.keys(), activo=True)
            .order_by("pk")
        )
        por_id = {p.pk: p for p in productos}
        if len(por_id) != len(cantidades):
            raise VentaError("Alguno de los productos ya no está disponible.")

        venta = Venta.objects.create(vendedor=vendedor, cliente=cliente)
        total = Decimal("0.00")
        for pid in sorted(cantidades):
            producto = por_id[pid]
            cantidad = cantidades[pid]
            if cantidad > producto.stock:
                raise VentaError(
                    f"Stock insuficiente de «{producto.nombre}»: "
                    f"disponible {producto.stock}, solicitado {cantidad}."
                )
            producto.stock -= cantidad
            producto.save(update_fields=["stock", "actualizado"])
            detalle = DetalleVenta.objects.create(
                venta=venta, producto=producto, cantidad=cantidad, precio_unitario=producto.precio
            )
            total += detalle.subtotal
        venta.total = total
        venta.save(update_fields=["total"])
    return venta
