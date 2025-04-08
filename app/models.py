from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db, login_manager


class User(db.Model, UserMixin):
    __tablename__ = 'user'  # Явно укажите имя таблицы

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    count_generations = db.Column(db.Integer, default=0)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)  # Хешируем пароль

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)  # Проверяем пароль

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))