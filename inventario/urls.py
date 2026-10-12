from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

urlpatterns = [
    path("", views.ProductoListView.as_view(), name="producto_lista"),
    path("resumen/", views.resumen, name="resumen"),
    path("productos/nuevo/", views.ProductoCreateView.as_view(), name="producto_nuevo"),
    path("productos/<int:pk>/editar/", views.ProductoUpdateView.as_view(), name="producto_editar"),
    path("ventas/", views.venta_lista, name="venta_lista"),
    path("ventas/checkout/", views.venta_checkout, name="venta_checkout"),
    path("ventas/<int:pk>/", views.venta_detalle, name="venta_detalle"),
]

# Imágenes subidas (solo en desarrollo)
if settings.DEBUG and settings.MEDIA_URL:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
