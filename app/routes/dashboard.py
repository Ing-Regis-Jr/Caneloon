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
    ventas_recientes = Venta.query.order_by(Venta.fecha.desc()).limit(8).all()
    productos_disponibles = (
        Producto.query.filter(Producto.stock > 0).order_by(Producto.nombre).all()
    )

    return render_template(
        "dashboard/index.html",
        resumen=resumen,
        ventas_recientes=ventas_recientes,
        productos_disponibles=productos_disponibles,
        formatear_moneda=formatear_moneda,
    )
