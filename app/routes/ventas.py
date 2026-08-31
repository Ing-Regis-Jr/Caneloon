from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Cliente, Producto, Venta
from app.services import StatsService, VentaService
from app.utils import formatear_moneda

ventas_bp = Blueprint("ventas", __name__, url_prefix="/ventas")


def _productos_para_edicion(venta: Venta) -> list[dict]:
    detalle = venta.detalles[0]
    producto_actual_id = detalle.id_producto
    cantidad_actual = detalle.cantidad
    productos = []

    for producto in Producto.query.order_by(Producto.nombre).all():
        if producto.stock > 0 or producto.id_producto == producto_actual_id:
            stock_disponible = producto.stock + (
                cantidad_actual if producto.id_producto == producto_actual_id else 0
            )
            productos.append(
                {
                    "id_producto": producto.id_producto,
                    "nombre": producto.nombre,
                    "precio_venta": producto.precio_venta,
                    "stock_disponible": stock_disponible,
                }
            )

    return productos


def _resolver_id_cliente() -> int | None:
    id_cliente = request.form.get("id_cliente") or None
    nombre_cliente = request.form.get("nombre_cliente", "").strip()

    if nombre_cliente:
        cliente = VentaService.obtener_o_crear_cliente(nombre_cliente)
        return cliente.id_cliente
    if id_cliente:
        return int(id_cliente)
    return None


@ventas_bp.route("/")
@login_required
def index():
    resumen = StatsService.resumen_general()
    productos_top = StatsService.productos_mas_vendidos()
    clientes_top = StatsService.clientes_top()
    historial = Venta.query.order_by(Venta.fecha.desc()).limit(20).all()

    return render_template(
        "ventas/index.html",
        resumen=resumen,
        productos_top=productos_top,
        clientes_top=clientes_top,
        historial=historial,
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
                id_producto=int(request.form["id_producto"]),
                cantidad=int(request.form["cantidad"]),
                id_cliente=_resolver_id_cliente(),
            )
            flash("Venta registrada correctamente.", "success")
            return redirect(url_for("ventas.index"))
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

    detalle = venta.detalles[0]
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    productos = _productos_para_edicion(venta)

    if request.method == "POST":
        try:
            VentaService.actualizar_venta(
                id_venta=id_venta,
                id_producto=int(request.form["id_producto"]),
                cantidad=int(request.form["cantidad"]),
                id_cliente=_resolver_id_cliente(),
            )
            flash("Venta actualizada correctamente.", "success")
            return redirect(url_for("ventas.index"))
        except (ValueError, KeyError) as exc:
            flash(str(exc) if str(exc) else "Datos inválidos.", "danger")

    return render_template(
        "ventas/editar.html",
        venta=venta,
        detalle=detalle,
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
