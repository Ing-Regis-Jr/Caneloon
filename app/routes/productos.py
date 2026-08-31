from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Producto
from app.utils import formatear_moneda

productos_bp = Blueprint("productos", __name__, url_prefix="/productos")


@productos_bp.route("/")
@login_required
def index():
    busqueda = request.args.get("q", "").strip()
    query = Producto.query
    if busqueda:
        query = query.filter(Producto.nombre.ilike(f"%{busqueda}%"))
    productos = query.order_by(Producto.nombre).all()
    return render_template(
        "productos/index.html",
        productos=productos,
        busqueda=busqueda,
        formatear_moneda=formatear_moneda,
    )


@productos_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    if request.method == "POST":
        try:
            producto = Producto(
                nombre=request.form["nombre"].strip(),
                precio_venta=float(request.form["precio_venta"]),
                costo_unitario=float(request.form["costo_unitario"]),
                stock=int(request.form["stock"]),
            )
            if producto.precio_venta < 0 or producto.costo_unitario < 0 or producto.stock < 0:
                raise ValueError("Los valores no pueden ser negativos.")
            db.session.add(producto)
            db.session.commit()
            flash("Producto registrado correctamente.", "success")
            return redirect(url_for("productos.index"))
        except (ValueError, KeyError) as exc:
            flash(str(exc) if str(exc) else "Datos inválidos.", "danger")

    return render_template("productos/form.html", producto=None, titulo="Nuevo producto")


@productos_bp.route("/<int:id_producto>/editar", methods=["GET", "POST"])
@login_required
def editar(id_producto: int):
    producto = db.session.get(Producto, id_producto)
    if not producto:
        flash("Producto no encontrado.", "warning")
        return redirect(url_for("productos.index"))

    if request.method == "POST":
        try:
            producto.nombre = request.form["nombre"].strip()
            producto.precio_venta = float(request.form["precio_venta"])
            producto.costo_unitario = float(request.form["costo_unitario"])
            producto.stock = int(request.form["stock"])
            if producto.precio_venta < 0 or producto.costo_unitario < 0 or producto.stock < 0:
                raise ValueError("Los valores no pueden ser negativos.")
            db.session.commit()
            flash("Producto actualizado.", "success")
            return redirect(url_for("productos.index"))
        except (ValueError, KeyError) as exc:
            flash(str(exc) if str(exc) else "Datos inválidos.", "danger")

    return render_template("productos/form.html", producto=producto, titulo="Editar producto")


@productos_bp.route("/<int:id_producto>/eliminar", methods=["POST"])
@login_required
def eliminar(id_producto: int):
    producto = db.session.get(Producto, id_producto)
    if not producto:
        flash("Producto no encontrado.", "warning")
        return redirect(url_for("productos.index"))

    if producto.detalles.count() > 0:
        flash("No se puede eliminar: el producto tiene ventas registradas.", "warning")
        return redirect(url_for("productos.index"))

    db.session.delete(producto)
    db.session.commit()
    flash("Producto eliminado.", "info")
    return redirect(url_for("productos.index"))
