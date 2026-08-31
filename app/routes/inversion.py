from flask import Blueprint, render_template
from flask_login import login_required

from app.services import StatsService
from app.utils import formatear_moneda

inversion_bp = Blueprint("inversion", __name__, url_prefix="/inversion")


@inversion_bp.route("/")
@login_required
def index():
    resumen = StatsService.resumen_general()
    productos_inversion = StatsService.inversion_por_producto()

    return render_template(
        "inversion/index.html",
        resumen=resumen,
        productos_inversion=productos_inversion,
        formatear_moneda=formatear_moneda,
    )
