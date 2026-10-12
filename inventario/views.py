import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from .forms import ProductoForm
from .models import Producto, Venta
from .services import VentaError, registrar_venta

LIMITE_VENTAS = 20
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


# ------------------ Productos ----------------------------------------------
class ProductoListView(LoginRequiredMixin, ListView):
    """Productos en stock (tarjetas) con precio, descripción y carrito de compra."""
    model = Producto
    template_name = "inventario/producto_list.html"
    context_object_name = "productos"
    paginate_by = 16

    def get_queryset(self):
        qs = Producto.objects.select_related("categoria")
        if self.request.GET.get("todos") != "1":
            qs = qs.filter(activo=True, stock__gt=0)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(sku__icontains=q) | Q(descripcion__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "").strip()
        ctx["todos"] = self.request.GET.get("todos") == "1"
        return ctx


class ProductoCreateView(LoginRequiredMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = "inventario/producto_form.html"
    success_url = reverse_lazy("producto_lista")

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        messages.success(self.request, "Producto registrado.")
        return super().form_valid(form)


class ProductoUpdateView(LoginRequiredMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = "inventario/producto_form.html"
    success_url = reverse_lazy("producto_lista")

    def form_valid(self, form):
        messages.success(self.request, "Producto actualizado.")
        return super().form_valid(form)


# ------------------ Ventas -------------------------------------------------
def _parse_fecha(valor):
    try:
        return date.fromisoformat(valor) if valor else None
    except ValueError:
        return None


@login_required
def venta_lista(request):
    """Últimas 20 ventas, con filtro opcional por rango de fechas."""
    desde = _parse_fecha(request.GET.get("desde"))
    hasta = _parse_fecha(request.GET.get("hasta"))
    if desde and hasta and desde > hasta:
        desde, hasta = hasta, desde
        messages.info(request, "Las fechas estaban invertidas; se intercambiaron.")

    tz = timezone.get_current_timezone()
    qs = Venta.objects.select_related("vendedor")
    if desde:
        qs = qs.filter(fecha__gte=timezone.make_aware(datetime.combine(desde, time.min), tz))
    if hasta:
        qs = qs.filter(
            fecha__lt=timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), tz)
        )

    resumen_rango = qs.aggregate(cantidad=Count("id"), suma=Sum("total"))
    ventas = list(qs.order_by("-fecha", "-id")[:LIMITE_VENTAS])
    return render(request, "inventario/venta_list.html", {
        "ventas": ventas,
        "desde": desde.isoformat() if desde else "",
        "hasta": hasta.isoformat() if hasta else "",
        "cantidad": resumen_rango["cantidad"],
        "suma": resumen_rango["suma"] or Decimal("0"),
        "limite": LIMITE_VENTAS,
        "hay_mas": resumen_rango["cantidad"] > LIMITE_VENTAS,
    })


@login_required
@require_POST
def venta_checkout(request):
    """Recibe el carrito (JSON) y registra la venta."""
    try:
        datos = json.loads(request.body)
        items = datos["items"]
        cliente = str(datos.get("cliente", "")).strip()[:150]
        if not isinstance(items, list):
            raise TypeError
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"ok": False, "error": "Solicitud inválida."}, status=400)
    try:
        venta = registrar_venta(request.user, cliente, items)
    except VentaError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    messages.success(request, f"Venta #{venta.pk} registrada.")
    return JsonResponse({"ok": True, "url": reverse("venta_detalle", args=[venta.pk])})


@login_required
def venta_detalle(request, pk):
    venta = get_object_or_404(
        Venta.objects.select_related("vendedor").prefetch_related("detalles__producto"), pk=pk
    )
    return render(request, "inventario/venta_detail.html", {"venta": venta})


# ------------------ Resumen ------------------------------------------------
@login_required
def resumen(request):
    hoy = timezone.localdate()

    # Últimos 12 meses (el último es el mes en curso)
    meses = []
    y, m = hoy.year, hoy.month
    for _ in range(12):
        meses.append((y, m))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    meses.reverse()

    inicio = timezone.make_aware(datetime(meses[0][0], meses[0][1], 1))
    filas = (
        Venta.objects.filter(fecha__gte=inicio)
        .annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(suma=Sum("total"), cantidad=Count("id"))
        .order_by()
    )
    por_mes = {(f["mes"].year, f["mes"].month): f for f in filas}

    serie = []
    for (anio, mes) in meses:
        f = por_mes.get((anio, mes))
        serie.append({
            "anio": anio,
            "etiqueta": MESES[mes - 1],
            "total": f["suma"] if f else Decimal("0"),
            "n": f["cantidad"] if f else 0,
        })

    max_total = max(s["total"] for s in serie)
    base = max_total if max_total > 0 else Decimal("1")
    for s in serie:
        s["pct"] = max(int(s["total"] * 100 / base), 3) if s["n"] else 0

    # Promedio mensual: meses COMPLETOS desde el primer mes con ventas hasta el anterior al actual.
    actual = serie[-1]
    primero = next((i for i, s in enumerate(serie) if s["n"] > 0), None)
    if primero is None:
        prom_total, prom_n, meses_base = Decimal("0"), 0, 0
    elif primero == len(serie) - 1:
        prom_total, prom_n, meses_base = actual["total"], actual["n"], 0
    else:
        completos = serie[primero:-1]
        meses_base = len(completos)
        prom_total = sum(s["total"] for s in completos) / meses_base
        prom_n = sum(s["n"] for s in completos) / meses_base

    variacion = None
    if meses_base and prom_total > 0:
        variacion = int(round((actual["total"] - prom_total) * 100 / prom_total))

    if prom_n:
        pct_ventas = min(100, int(actual["n"] * 100 / prom_n))
    else:
        pct_ventas = 100 if actual["n"] else 0

    en_stock = Producto.objects.filter(activo=True, stock__gt=0).count()
    agotados = Producto.objects.filter(activo=True, stock=0).count()
    activos = en_stock + agotados

    def pct(x):
        return int(x * 100 / activos) if activos else 0

    valor_inventario = Producto.objects.filter(activo=True).aggregate(
        v=Sum(ExpressionWrapper(
            F("precio") * F("stock"), output_field=DecimalField(max_digits=18, decimal_places=2)
        ))
    )["v"] or Decimal("0")

    gauges = [
        {"value": actual["n"], "offset": 100 - pct_ventas, "color": "teal",
         "label": "Ventas del mes", "hint": "frente al promedio mensual de ventas"},
        {"value": en_stock, "offset": 100 - pct(en_stock), "color": "blue",
         "label": "En stock", "hint": f"de {activos} productos activos"},
        {"value": agotados, "offset": 100 - pct(agotados), "color": "purple",
         "label": "Agotados", "hint": f"de {activos} productos activos"},
    ]

    return render(request, "inventario/resumen.html", {
        "gauges": gauges,
        "serie": serie,
        "max_total": max_total,
        "hay_ventas": any(s["n"] for s in serie),
        "actual": actual,
        "prom_total": prom_total,
        "prom_n": prom_n,
        "meses_base": meses_base,
        "variacion": variacion,
        "valor_inventario": valor_inventario,
        "hoy": hoy,
    })
