
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Producto
from app.services import StatsService
from app.utils import formatear_moneda

productos_bp = Blueprint("productos", __name__, url_prefix="/productos")


@productos_bp.route("/")
@login_required
def index():
    busqueda = request.args.get("q", "").strip()
    estado = request.args.get("estado", "activos").strip().lower()

    mostrar_archivados = estado == "archivados"

    query = Producto.query.filter(
        Producto.activo.is_(not mostrar_archivados)
    )

    if busqueda:
        query = query.filter(
            Producto.nombre.ilike(f"%{busqueda}%")
        )

    productos = query.order_by(Producto.nombre).all()

    productos_activos = Producto.query.filter(
        Producto.activo.is_(True)
    ).all()

    productos_archivados = Producto.query.filter(
        Producto.activo.is_(False)
    ).count()

    resumen = StatsService.resumen_general()

    stock_total = sum(
        producto.stock
        for producto in productos_activos
    )

    valor_venta_potencial = sum(
        producto.precio_venta * producto.stock
        for producto in productos_activos
    )

    inversion_inventario = sum(
        producto.costo_unitario * producto.stock
        for producto in productos_activos
    )

    productos_stock_bajo = sum(
        1
        for producto in productos_activos
        if producto.stock <= 5
    )

    return render_template(
        "productos/index.html",
        productos=productos,
        busqueda=busqueda,
        estado=estado,
        mostrar_archivados=mostrar_archivados,
        total_productos=len(productos_activos),
        productos_archivados=productos_archivados,
        stock_total=stock_total,
        inversion_inventario=inversion_inventario,
        valor_venta_potencial=valor_venta_potencial,
        productos_stock_bajo=productos_stock_bajo,
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
                activo=True,
            )

            if not producto.nombre:
                raise ValueError("El nombre es obligatorio.")

            if (
                producto.precio_venta < 0
                or producto.costo_unitario < 0
                or producto.stock < 0
            ):
                raise ValueError(
                    "Los valores no pueden ser negativos."
                )

            db.session.add(producto)
            db.session.commit()

            flash(
                "Producto registrado correctamente.",
                "success",
            )

            return redirect(url_for("productos.index"))

        except (ValueError, KeyError) as exc:
            flash(
                str(exc) if str(exc) else "Datos inválidos.",
                "danger",
            )

    return render_template(
        "productos/form.html",
        producto=None,
        titulo="Nuevo producto",
    )


@productos_bp.route(
    "/<int:id_producto>/editar",
    methods=["GET", "POST"],
)
@login_required
def editar(id_producto: int):
    producto = db.session.get(Producto, id_producto)

    if not producto:
        flash(
            "Producto no encontrado.",
            "warning",
        )
        return redirect(url_for("productos.index"))

    if request.method == "POST":
        try:
            nombre = request.form["nombre"].strip()
            precio_venta = float(request.form["precio_venta"])
            costo_unitario = float(request.form["costo_unitario"])
            stock = int(request.form["stock"])

            if not nombre:
                raise ValueError(
                    "El nombre es obligatorio."
                )

            if (
                precio_venta < 0
                or costo_unitario < 0
                or stock < 0
            ):
                raise ValueError(
                    "Los valores no pueden ser negativos."
                )

            producto.nombre = nombre
            producto.precio_venta = precio_venta
            producto.costo_unitario = costo_unitario
            producto.stock = stock

            db.session.commit()

            flash(
                "Producto actualizado.",
                "success",
            )

            return redirect(
                url_for(
                    "productos.index",
                    estado=(
                        "archivados"
                        if not producto.activo
                        else "activos"
                    ),
                )
            )

        except (ValueError, KeyError) as exc:
            flash(
                str(exc) if str(exc) else "Datos inválidos.",
                "danger",
            )

    return render_template(
        "productos/form.html",
        producto=producto,
        titulo="Editar producto",
    )


@productos_bp.route(
    "/<int:id_producto>/archivar",
    methods=["POST"],
)
@login_required
def archivar(id_producto: int):
    producto = db.session.get(Producto, id_producto)

    if not producto:
        flash(
            "Producto no encontrado.",
            "warning",
        )
        return redirect(url_for("productos.index"))

    if not producto.activo:
        flash(
            "El producto ya está archivado.",
            "info",
        )
        return redirect(url_for("productos.index"))


    producto.activo = False
    db.session.commit()

    if producto.stock > 0:
        flash(
            (
                f"{producto.nombre} fue archivado. "
                f"Tenía {producto.stock} unidades en stock, "
                "que quedarán fuera de las nuevas ventas."
            ),
            "warning",
        )
    else:
        flash(
            f"{producto.nombre} fue archivado correctamente.",
            "success",
        )

    return redirect(url_for("productos.index"))


@productos_bp.route(
    "/<int:id_producto>/restaurar",
    methods=["POST"],
)
@login_required
def restaurar(id_producto: int):
    producto = db.session.get(Producto, id_producto)

    if not producto:
        flash(
            "Producto no encontrado.",
            "warning",
        )
        return redirect(
            url_for(
                "productos.index",
                estado="archivados",
            )
        )

    if producto.activo:
        flash(
            "El producto ya está activo.",
            "info",
        )
        return redirect(url_for("productos.index"))

    producto.activo = True
    db.session.commit()

    flash(
        f"{producto.nombre} volvió a estar disponible.",
        "success",
    )

    return redirect(url_for("productos.index"))


@productos_bp.route(
    "/<int:id_producto>/eliminar",
    methods=["POST"],
)
@login_required
def eliminar(id_producto: int):
    producto = db.session.get(Producto, id_producto)

    if not producto:
        flash(
            "Producto no encontrado.",
            "warning",
        )
        return redirect(url_for("productos.index"))

    if producto.detalles.count() > 0:
        flash(
            "No se puede eliminar: el producto tiene ventas registradas. "
            "Puedes archivarlo para conservar su historial.",
            "warning",
        )
        return redirect(
            url_for(
                "productos.index",
                estado=(
                    "archivados"
                    if not producto.activo
                    else "activos"
                ),
            )
        )

    db.session.delete(producto)
    db.session.commit()

    flash(
        "Producto eliminado.",
        "info",
    )

    return redirect(
        url_for(
            "productos.index",
            estado=(
                "archivados"
                if not producto.activo
                else "activos"
            ),
        )
    )