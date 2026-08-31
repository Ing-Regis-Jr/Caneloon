from flask import Flask
from flask_login import current_user

from app.config import Config
from app.extensions import db, login_manager
from app.models import Usuario


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.clientes import clientes_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.inversion import inversion_bp
    from app.routes.productos import productos_bp
    from app.routes.ventas import ventas_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(ventas_bp)
    app.register_blueprint(inversion_bp)
    app.register_blueprint(clientes_bp)

    @app.context_processor
    def inject_globals():
        return {
            "app_name": "DULCE LIMON",
            "usuario_actual": current_user if current_user.is_authenticated else None,
        }

    with app.app_context():
        db.create_all()
        _crear_usuario_inicial()

    return app


def _crear_usuario_inicial() -> None:
    if not Usuario.query.filter_by(username="admin").first():
        usuario = Usuario(username="admin")
        usuario.set_password("admin123")
        db.session.add(usuario)
        db.session.commit()
