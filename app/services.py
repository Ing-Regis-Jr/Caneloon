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
    def _normalizar_items(items: list[tuple[int, int]]) -> dict[int, int]:
        """Une productos repetidos y valida cantidades."""
        agrupados: dict[int, int] = {}
        for id_producto, cantidad in items:
            if cantidad <= 0:
                raise ValueError("La cantidad debe ser mayor a cero.")
            agrupados[id_producto] = agrupados.get(id_producto, 0) + cantidad
        if not agrupados:
            raise ValueError("Agrega al menos un producto a la venta.")
        return agrupados

    @staticmethod
    def _aplicar_items(
        venta: Venta,
        items: dict[int, int],
        productos_archivados_permitidos: set[int] | None = None,
    ) -> None:
        """Crea los detalles y descuenta stock."""
        total = 0.0

        for id_producto, cantidad in items.items():
            producto = db.session.get(Producto, id_producto)

            if not producto:
                raise ValueError("Producto no encontrado.")

            if (
    not producto.activo
    and id_producto not in (productos_archivados_permitidos or set())
):
                raise ValueError(
                    f"El producto {producto.nombre} está archivado "
                    "y no puede utilizarse en nuevas ventas."
                )

            if producto.stock < cantidad:
                raise ValueError(
                    f"Stock insuficiente para {producto.nombre}. "
                    f"Disponible: {producto.stock}."
                )

            subtotal = producto.precio_venta * cantidad
            costo_total = producto.costo_unitario * cantidad

            venta.detalles.append(
                DetalleVenta(
                    id_producto=producto.id_producto,
                    cantidad=cantidad,
                    precio_unitario=producto.precio_venta,
                    subtotal=subtotal,
                    costo_total=costo_total,
                    ganancia=subtotal
                )
            )

            producto.stock -= cantidad
            total += subtotal

        venta.total = total

    @staticmethod
    def registrar_venta(
        items: list[tuple[int, int]],
        id_cliente: int | None,
    ) -> Venta:
        agrupados = VentaService._normalizar_items(items)
        venta = Venta(id_cliente=id_cliente, total=0.0)

        try:
            # Las ventas nuevas solo admiten productos activos.
            VentaService._aplicar_items(venta, agrupados)

            db.session.add(venta)
            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        return venta

    @staticmethod
    def actualizar_venta(
        id_venta: int,
        items: list[tuple[int, int]],
        id_cliente: int | None,
    ) -> Venta:
        venta = db.session.get(Venta, id_venta)

        if not venta or not venta.detalles:
            raise ValueError("Venta no encontrada.")

        # Guardamos los productos que ya pertenecían a esta venta.
        productos_originales = {
            detalle.id_producto for detalle in venta.detalles
        }

        agrupados = VentaService._normalizar_items(items)

        try:
            # Devolvemos al inventario las cantidades de la venta anterior.
            for detalle in list(venta.detalles):
                detalle.producto.stock += detalle.cantidad

            venta.detalles.clear()
            db.session.flush()

            venta.id_cliente = id_cliente

            # Solo permite conservar productos archivados que ya estaban
            # incluidos en esta venta antes de editarla.
            VentaService._aplicar_items(
                venta,
                agrupados,
                productos_archivados_permitidos=productos_originales,
            )

            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        return venta

    @staticmethod
    def eliminar_venta(id_venta: int) -> None:
        venta = db.session.get(Venta, id_venta)
        if not venta or not venta.detalles:
            raise ValueError("Venta no encontrada.")

        for detalle in venta.detalles:
            detalle.producto.stock += detalle.cantidad
        db.session.delete(venta)
        db.session.commit()


class StatsService:
    @staticmethod
    def resumen_general() -> ResumenFinanciero:
        ventas_totales = db.session.query(
            func.coalesce(func.sum(Venta.total), 0.0)
        ).scalar()
        costo_total = db.session.query(
            func.coalesce(func.sum(DetalleVenta.costo_total), 0.0)
        ).scalar()
        ganancia_neta = db.session.query(
            func.coalesce(func.sum(DetalleVenta.ganancia), 0.0)
        ).scalar()

        productos = Producto.query.all()
        inversion_inventario = sum(p.costo_unitario * p.stock for p in productos)
        umbral = current_app.config["STOCK_BAJO_UMBRAL"]
        productos_stock_bajo = sum(1 for p in productos if p.stock <= umbral)

        porcentaje = (
            (ganancia_neta / ventas_totales * 100) if ventas_totales > 0 else 0.0
        )

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
        return [
            (r.nombre, int(r.total_vendido or 0), float(r.ingresos or 0))
            for r in resultados
        ]

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
        return [
            (r.nombre, int(r.total_compras or 0), float(r.total_gastado or 0))
            for r in resultados
        ]

    @staticmethod
    def clientes_resumen(busqueda: str = "") -> list[dict]:
        query = (
            db.session.query(
                Cliente.id_cliente,
                Cliente.nombre,
                func.count(Venta.id_venta).label("compras"),
                func.coalesce(func.sum(Venta.total), 0.0).label("gastado"),
                func.max(Venta.fecha).label("ultima_compra"),
            )
            .outerjoin(Venta, Venta.id_cliente == Cliente.id_cliente)
            .group_by(Cliente.id_cliente)
            .order_by(Cliente.nombre)
        )
        if busqueda:
            query = query.filter(Cliente.nombre.ilike(f"%{busqueda}%"))

        return [
            {
                "id_cliente": r.id_cliente,
                "nombre": r.nombre,
                "compras": int(r.compras),
                "gastado": float(r.gastado),
                "ultima_compra": r.ultima_compra,
            }
            for r in query.all()
        ]

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
                "margen_porcentaje": (
                    (p.precio_venta - p.costo_unitario) / p.precio_venta * 100
                    if p.precio_venta > 0
                    else 0.0
                ),
            }
            for p in productos
        ]
