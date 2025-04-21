from flask import Flask

from app.api import api_bp  # Добавьте этот импорт
from app.auth import auth_bp
from app.extensions import db, login_manager
from app.main import main_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    login_manager.init_app(app)

    # Регистрируем Blueprint
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')  # Добавьте эту строку

    with app.app_context():
        db.create_all()

    return app
