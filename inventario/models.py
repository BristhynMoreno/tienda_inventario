from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    sku = models.CharField("código (SKU)", max_length=50, unique=True)
    nombre = models.CharField(max_length=150, db_index=True)
    descripcion = models.TextField("descripción", blank=True)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, null=True, blank=True, related_name="productos"
    )
    precio = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    stock = models.PositiveIntegerField(default=0)
    imagen = models.ImageField("imagen", upload_to="productos/", blank=True)
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="productos_creados"
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        indexes = [models.Index(fields=["activo", "stock"])]

    def __str__(self):
        return f"{self.nombre} ({self.sku})"


class Venta(models.Model):
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ventas"
    )
    cliente = models.CharField(max_length=150, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Venta #{self.pk} - {self.fecha:%Y-%m-%d}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="ventas")
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # Se guarda el precio al momento de la venta: si el precio cambia, el historial no.
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"
