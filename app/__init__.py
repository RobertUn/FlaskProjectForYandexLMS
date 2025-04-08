from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from app.routes import auth_bp
from app.extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()  # Создаст таблицы при первом запуске

    # Регистрируем Blueprint
    app.register_blueprint(auth_bp, url_prefix='/auth')  # URL будет /auth/login, /auth/register

    return app


