import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
STOCK_BAJO_UMBRAL = 5
MONEDA_SIMBOLO = "Bs."


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dulce-limon-dev-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STOCK_BAJO_UMBRAL = STOCK_BAJO_UMBRAL
    MONEDA_SIMBOLO = MONEDA_SIMBOLO
