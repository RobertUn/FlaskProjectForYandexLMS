import os

from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()


class Config:
    # Секретный ключ Flask (защита от CSRF и сессий)
    SECRET_KEY = os.getenv('SECRET_KEY') or 'default-key-if-not-set'

    # Настройки БД (SQLite по умолчанию)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Папка для загрузки CSV
    UPLOAD_FOLDER = 'app/static/uploads'
    ALLOWED_EXTENSIONS = {'csv'}


config = Config()
