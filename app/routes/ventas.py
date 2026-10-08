from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Cliente, Producto, Venta
from app.services import VentaService
from app.utils import formatear_moneda
from datetime import date, datetime, time, timedelta

from sqlalchemy import func
ventas_bp = Blueprint("ventas", __name__, url_prefix="/ventas")


def _productos_para_edicion(venta: Venta) -> list[dict]:
    en_venta = {d.id_producto: d.cantidad for d in venta.detalles}
    productos = []

    for producto in Producto.query.order_by(Producto.nombre).all():
        if producto.stock > 0 or producto.id_producto in en_venta:
            productos.append(
                {
                    "id_producto": producto.id_producto,
                    "nombre": producto.nombre,
                    "precio_venta": producto.precio_venta,
                    "stock_disponible": producto.stock + en_venta.get(producto.id_producto, 0),
                }
            )

    return productos


def _leer_items() -> list[tuple[int, int]]:
    ids = request.form.getlist("id_producto")
    cantidades = request.form.getlist("cantidad")
    items = []
    for id_producto, cantidad in zip(ids, cantidades):
        if not id_producto:
            continue
        items.append((int(id_producto), int(cantidad)))
    return items

def _resolver_id_cliente() -> int | None:
    id_cliente = request.form.get("id_cliente") or None
    nombre_cliente = request.form.get("nombre_cliente", "").strip()

    if nombre_cliente:
        cliente = VentaService.obtener_o_crear_cliente(nombre_cliente)
        return cliente.id_cliente
    if id_cliente:
        return int(id_cliente)
    return None


def _parse_fecha(valor: str | None) -> date | None:
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


@ventas_bp.route("/")
@login_required
def index():
    desde = _parse_fecha(request.args.get("desde"))
    hasta = _parse_fecha(request.args.get("hasta"))
    if desde and hasta and desde > hasta:
        desde, hasta = hasta, desde

    query = Venta.query
    if desde:
        query = query.filter(Venta.fecha >= datetime.combine(desde, time.min))
    if hasta:
        query = query.filter(Venta.fecha <= datetime.combine(hasta, time.max))

    cantidad = query.count()
    total_periodo = query.with_entities(
        func.coalesce(func.sum(Venta.total), 0.0)
    ).scalar()
    historial = query.order_by(Venta.fecha.desc()).limit(200).all()

    desde_str = desde.isoformat() if desde else ""
    hasta_str = hasta.isoformat() if hasta else ""

    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    atajos = [
        {
            "nombre": nombre,
            "desde": d.isoformat(),
            "hasta": h.isoformat(),
            "activo": d.isoformat() == desde_str and h.isoformat() == hasta_str,
        }
        for nombre, d, h in [
            ("Hoy", hoy, hoy),
            ("Ayer", ayer, ayer),
            ("7 días", hoy - timedelta(days=6), hoy),
            ("Este mes", hoy.replace(day=1), hoy),
        ]
    ]

    return render_template(
        "ventas/index.html",
        historial=historial,
        cantidad=cantidad,
        total_periodo=total_periodo,
        desde_str=desde_str,
        hasta_str=hasta_str,
        atajos=atajos,
        formatear_moneda=formatear_moneda,
    )


@ventas_bp.route("/registrar", methods=["GET", "POST"])
@login_required
def registrar():
    productos = Producto.query.filter(Producto.stock > 0).order_by(Producto.nombre).all()
    clientes = Cliente.query.order_by(Cliente.nombre).all()

    if request.method == "POST":
        try:
            VentaService.registrar_venta(
                items=_leer_items(),
                id_cliente=_resolver_id_cliente(),
            )
            flash("Venta registrada correctamente.", "success")
            return redirect(url_for("dashboard.index"))
        except (ValueError, KeyError) as exc:
            flash(str(exc) if str(exc) else "Datos inválidos.", "danger")

    return render_template(
        "ventas/registrar.html",
        productos=productos,
        clientes=clientes,
        formatear_moneda=formatear_moneda,
    )


@ventas_bp.route("/<int:id_venta>/editar", methods=["GET", "POST"])
@login_required
def editar(id_venta: int):
    venta = db.session.get(Venta, id_venta)
    if not venta or not venta.detalles:
        flash("Venta no encontrada.", "warning")
        return redirect(url_for("ventas.index"))

    
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    productos = _productos_para_edicion(venta)

    if request.method == "POST":
        try:
            VentaService.actualizar_venta(
                id_venta=id_venta,
                items=_leer_items(),
                id_cliente=_resolver_id_cliente(),
            )
            flash("Venta actualizada correctamente.", "success")
            return redirect(url_for("ventas.index"))
        except (ValueError, KeyError) as exc:
            flash(str(exc) if str(exc) else "Datos inválidos.", "danger")

    return render_template(
        "ventas/editar.html",
        venta=venta,
        items_iniciales=[
            {"id": d.id_producto, "cantidad": d.cantidad} for d in venta.detalles],
        productos=productos,
        clientes=clientes,
        formatear_moneda=formatear_moneda,
    )


@ventas_bp.route("/<int:id_venta>/eliminar", methods=["POST"])
@login_required
def eliminar(id_venta: int):
    try:
        VentaService.eliminar_venta(id_venta)
        flash("Venta eliminada. El stock fue restaurado.", "info")
    except ValueError as exc:
        flash(str(exc), "warning")

    return redirect(url_for("ventas.index"))
