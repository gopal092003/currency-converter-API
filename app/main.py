from flask import Flask
from app.routes.currency import currency_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(currency_bp)

    return app