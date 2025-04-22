import os

from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()


class Config:
    UPLOAD_FOLDER = os.path.abspath('instance/temp_uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    DOWNLOAD_TIMEOUT = 3600  # 1 hour

    # Создаем директории при инициализации
    def __init__(self):
        os.makedirs(self.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(os.path.join(self.UPLOAD_FOLDER, 'temp_certs'), exist_ok=True)

    # Секретный ключ Flask (защита от CSRF и сессий)
    SECRET_KEY = os.getenv('SECRET_KEY') or 'default-key-if-not-set'

    # Настройки БД (SQLite по умолчанию)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace("postgres://", "postgresql://",
                                                                         1) or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Папка для загрузки CSV
    UPLOAD_FOLDER = 'app/static/uploads'
    ALLOWED_EXTENSIONS = {'csv'}

    MAX_CONTENT_LENGTH = 50 * 1024 * 1024


config = Config()
