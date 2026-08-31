from flask import current_app


def formatear_moneda(monto: float) -> str:
    simbolo = current_app.config.get("MONEDA_SIMBOLO", "Bs.")
    return f"{simbolo} {monto:,.2f}"
