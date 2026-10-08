from datetime import datetime, time

from flask import Blueprint, render_template
from flask_login import login_required

from app.models import Producto, Venta
from app.services import StatsService
from app.utils import formatear_moneda

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    resumen = StatsService.resumen_general()

    inicio_hoy = datetime.combine(datetime.now().date(), time.min)
    fin_hoy = datetime.combine(datetime.now().date(), time.max)

    ventas_hoy = (
        Venta.query
        .filter(Venta.fecha >= inicio_hoy, Venta.fecha <= fin_hoy)
        .order_by(Venta.fecha.desc())
        .all()
    )

    productos = (
        Producto.query
        .filter(Producto.stock > 0, Producto.activo.is_(True),)
        .order_by(Producto.nombre)
        .all()
    )

    top_productos = StatsService.productos_mas_vendidos()
    top_clientes = StatsService.clientes_top()

    return render_template(
        "dashboard/index.html",
        resumen=resumen,
        ventas_hoy=ventas_hoy,
        productos=productos,
        top_productos=top_productos,
        top_clientes=top_clientes,
        formatear_moneda=formatear_moneda,
    )