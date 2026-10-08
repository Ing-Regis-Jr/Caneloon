
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Cliente
from app.services import StatsService
from app.utils import formatear_moneda

clientes_bp = Blueprint("clientes", __name__, url_prefix="/clientes")


@clientes_bp.route("/")
@login_required
def index():
    busqueda = request.args.get("q", "").strip()

    clientes = StatsService.clientes_resumen(busqueda)
    todos_los_clientes = StatsService.clientes_resumen()

    total_clientes = len(todos_los_clientes)
    clientes_con_compras = sum(
        1 for cliente in todos_los_clientes if cliente["compras"] > 0
    )
    total_gastado = sum(
        cliente["gastado"] for cliente in todos_los_clientes
    )

    return render_template(
        "clientes/index.html",
        clientes=clientes,
        busqueda=busqueda,
        total_clientes=total_clientes,
        clientes_con_compras=clientes_con_compras,
        total_gastado=total_gastado,
        formatear_moneda=formatear_moneda,
    )


@clientes_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()

        if not nombre:
            flash("El nombre es obligatorio.", "danger")
        else:
            db.session.add(Cliente(nombre=nombre))
            db.session.commit()
            flash("Cliente registrado.", "success")
            return redirect(url_for("clientes.index"))

    return render_template(
        "clientes/form.html",
        cliente=None,
        titulo="Nuevo cliente",
    )


@clientes_bp.route("/<int:id_cliente>/editar", methods=["GET", "POST"])
@login_required
def editar(id_cliente: int):
    cliente = db.session.get(Cliente, id_cliente)

    if not cliente:
        flash("Cliente no encontrado.", "warning")
        return redirect(url_for("clientes.index"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()

        if not nombre:
            flash("El nombre es obligatorio.", "danger")
        else:
            cliente.nombre = nombre
            db.session.commit()
            flash("Cliente actualizado.", "success")
            return redirect(url_for("clientes.index"))

    return render_template(
        "clientes/form.html",
        cliente=cliente,
        titulo="Editar cliente",
    )


@clientes_bp.route("/<int:id_cliente>/eliminar", methods=["POST"])
@login_required
def eliminar(id_cliente: int):
    cliente = db.session.get(Cliente, id_cliente)

    if not cliente:
        flash("Cliente no encontrado.", "warning")
        return redirect(url_for("clientes.index"))

    db.session.delete(cliente)
    db.session.commit()

    flash("Cliente eliminado.", "info")
    return redirect(url_for("clientes.index"))

