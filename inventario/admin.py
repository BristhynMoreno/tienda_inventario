from django.contrib import admin

from .models import Categoria, DetalleVenta, Producto, Venta


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "sku", "categoria", "precio", "stock", "activo"]
    list_filter = ["activo", "categoria"]
    search_fields = ["nombre", "sku"]


class DetalleInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ["producto", "cantidad", "precio_unitario"]
    can_delete = False


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ["id", "fecha", "vendedor", "cliente", "total"]
    list_filter = ["fecha", "vendedor"]
    inlines = [DetalleInline]
