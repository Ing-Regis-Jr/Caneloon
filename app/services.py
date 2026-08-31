from dataclasses import dataclass

from flask import current_app
from sqlalchemy import func

from app.extensions import db
from app.models import Cliente, DetalleVenta, Producto, Venta


@dataclass
class ResumenFinanciero:
    ventas_totales: float
    costo_total: float
    ganancia_neta: float
    inversion_inventario: float
    productos_registrados: int
    productos_stock_bajo: int
    porcentaje_ganancia: float


class VentaService:
    @staticmethod
    def obtener_o_crear_cliente(nombre: str) -> Cliente:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre del cliente no puede estar vacío.")

        cliente = Cliente.query.filter(
            func.lower(Cliente.nombre) == nombre.lower()
        ).first()
        if cliente:
            return cliente

        cliente = Cliente(nombre=nombre)
        db.session.add(cliente)
        db.session.flush()
        return cliente

    @staticmethod
    def registrar_venta(id_producto: int, cantidad: int, id_cliente: int | None) -> Venta:
        producto = db.session.get(Producto, id_producto)
        if not producto:
            raise ValueError("Producto no encontrado.")

        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a cero.")

        if producto.stock < cantidad:
            raise ValueError(
                f"Stock insuficiente. Disponible: {producto.stock}, solicitado: {cantidad}."
            )

        subtotal = producto.precio_venta * cantidad
        costo_total = producto.costo_unitario * cantidad
        ganancia = subtotal - costo_total

        venta = Venta(id_cliente=id_cliente, total=subtotal)
        detalle = DetalleVenta(
            producto=producto,
            cantidad=cantidad,
            precio_unitario=producto.precio_venta,
            subtotal=subtotal,
            costo_total=costo_total,
            ganancia=ganancia,
        )
        venta.detalles.append(detalle)

        producto.stock -= cantidad

        db.session.add(venta)
        db.session.commit()
        return venta

    @staticmethod
    def actualizar_venta(
        id_venta: int, id_producto: int, cantidad: int, id_cliente: int | None
    ) -> Venta:
        venta = db.session.get(Venta, id_venta)
        if not venta or not venta.detalles:
            raise ValueError("Venta no encontrada.")

        detalle = venta.detalles[0]
        producto_anterior = detalle.producto
        cantidad_anterior = detalle.cantidad
        producto_nuevo = db.session.get(Producto, id_producto)
        if not producto_nuevo:
            raise ValueError("Producto no encontrado.")

        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a cero.")

        if producto_nuevo.id_producto == producto_anterior.id_producto:
            stock_disponible = producto_nuevo.stock + cantidad_anterior
        else:
            stock_disponible = producto_nuevo.stock

        if stock_disponible < cantidad:
            raise ValueError(
                f"Stock insuficiente. Disponible: {stock_disponible}, solicitado: {cantidad}."
            )

        producto_anterior.stock += cantidad_anterior
        producto_nuevo.stock -= cantidad

        subtotal = producto_nuevo.precio_venta * cantidad
        costo_total = producto_nuevo.costo_unitario * cantidad
        ganancia = subtotal - costo_total

        detalle.id_producto = producto_nuevo.id_producto
        detalle.cantidad = cantidad
        detalle.precio_unitario = producto_nuevo.precio_venta
        detalle.subtotal = subtotal
        detalle.costo_total = costo_total
        detalle.ganancia = ganancia

        venta.id_cliente = id_cliente
        venta.total = subtotal

        db.session.commit()
        return venta

    @staticmethod
    def eliminar_venta(id_venta: int) -> None:
        venta = db.session.get(Venta, id_venta)
        if not venta or not venta.detalles:
            raise ValueError("Venta no encontrada.")

        detalle = venta.detalles[0]
        detalle.producto.stock += detalle.cantidad
        db.session.delete(venta)
        db.session.commit()


class StatsService:
    @staticmethod
    def resumen_general() -> ResumenFinanciero:
        ventas_totales = db.session.query(func.coalesce(func.sum(Venta.total), 0.0)).scalar()
        costo_total = db.session.query(func.coalesce(func.sum(DetalleVenta.costo_total), 0.0)).scalar()
        ganancia_neta = db.session.query(func.coalesce(func.sum(DetalleVenta.ganancia), 0.0)).scalar()

        productos = Producto.query.all()
        inversion_inventario = sum(p.costo_unitario * p.stock for p in productos)
        umbral = current_app.config["STOCK_BAJO_UMBRAL"]
        productos_stock_bajo = sum(1 for p in productos if p.stock <= umbral)

        porcentaje = (ganancia_neta / ventas_totales * 100) if ventas_totales > 0 else 0.0

        return ResumenFinanciero(
            ventas_totales=float(ventas_totales),
            costo_total=float(costo_total),
            ganancia_neta=float(ganancia_neta),
            inversion_inventario=float(inversion_inventario),
            productos_registrados=len(productos),
            productos_stock_bajo=productos_stock_bajo,
            porcentaje_ganancia=float(porcentaje),
        )

    @staticmethod
    def productos_mas_vendidos(limite: int = 5) -> list[tuple[str, int, float]]:
        resultados = (
            db.session.query(
                Producto.nombre,
                func.sum(DetalleVenta.cantidad).label("total_vendido"),
                func.sum(DetalleVenta.subtotal).label("ingresos"),
            )
            .join(DetalleVenta, DetalleVenta.id_producto == Producto.id_producto)
            .group_by(Producto.id_producto)
            .order_by(func.sum(DetalleVenta.cantidad).desc())
            .limit(limite)
            .all()
        )
        return [(r.nombre, int(r.total_vendido or 0), float(r.ingresos or 0)) for r in resultados]

    @staticmethod
    def clientes_top(limite: int = 5) -> list[tuple[str, int, float]]:
        resultados = (
            db.session.query(
                Cliente.nombre,
                func.count(Venta.id_venta).label("total_compras"),
                func.sum(Venta.total).label("total_gastado"),
            )
            .join(Venta, Venta.id_cliente == Cliente.id_cliente)
            .group_by(Cliente.id_cliente)
            .order_by(func.sum(Venta.total).desc())
            .limit(limite)
            .all()
        )
        return [(r.nombre, int(r.total_compras or 0), float(r.total_gastado or 0)) for r in resultados]

    @staticmethod
    def inversion_por_producto() -> list[dict]:
        productos = Producto.query.order_by(Producto.nombre).all()
        return [
            {
                "nombre": p.nombre,
                "stock": p.stock,
                "costo_unitario": p.costo_unitario,
                "inversion": p.costo_unitario * p.stock,
                "valor_venta_potencial": p.precio_venta * p.stock,
                "margen_unitario": p.precio_venta - p.costo_unitario,
            }
            for p in productos
        ]
