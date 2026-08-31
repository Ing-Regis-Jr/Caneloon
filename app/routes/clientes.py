from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Cliente

clientes_bp = Blueprint("clientes", __name__, url_prefix="/clientes")


@clientes_bp.route("/")
@login_required
def index():
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template("clientes/index.html", clientes=clientes)


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

    return render_template("clientes/form.html", cliente=None, titulo="Nuevo cliente")


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

    return render_template("clientes/form.html", cliente=cliente, titulo="Editar cliente")


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
