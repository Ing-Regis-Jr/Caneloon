from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Cliente(db.Model):
    __tablename__ = "clientes"

    id_cliente = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)

    ventas = db.relationship("Venta", back_populates="cliente", lazy="dynamic")


class Producto(db.Model):
    __tablename__ = "productos"

    id_producto = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    precio_venta = db.Column(db.Float, nullable=False)
    costo_unitario = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)

    detalles = db.relationship("DetalleVenta", back_populates="producto", lazy="dynamic")


class Venta(db.Model):
    __tablename__ = "ventas"

    id_venta = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.now)
    id_cliente = db.Column(db.Integer, db.ForeignKey("clientes.id_cliente"), nullable=True)
    total = db.Column(db.Float, nullable=False, default=0.0)

    cliente = db.relationship("Cliente", back_populates="ventas")
    detalles = db.relationship(
        "DetalleVenta",
        back_populates="venta",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class DetalleVenta(db.Model):
    __tablename__ = "detalles_venta"

    id_detalle = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, db.ForeignKey("ventas.id_venta"), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey("productos.id_producto"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    costo_total = db.Column(db.Float, nullable=False)
    ganancia = db.Column(db.Float, nullable=False)

    venta = db.relationship("Venta", back_populates="detalles")
    producto = db.relationship("Producto", back_populates="detalles")


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(Usuario, int(user_id))
