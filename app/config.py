import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-123')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', f'sqlite:///{os.path.join(basedir, "mappings.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULER_API_ENABLED = True

    ORDER_STATE_IDS = [
        'ee53314c-b442-11ee-0a80-16d90007f2e8',     # Подтвержден
        'ee5331fa-b442-11ee-0a80-16d90007f2ea',     # Ожидание отгрузки (Резерв)
        'bce7e955-c139-11ee-0a80-0cc60001a087',     # Отгружено
        'ee533246-b442-11ee-0a80-16d90007f2eb',     # Доставлен
    ]

    MS1_TOKEN = os.getenv('MS1_TOKEN')
    MS1_URL = os.getenv('MS1_URL', 'https://api.moysklad.ru')
    MS2_TOKEN = os.getenv('MS2_TOKEN')
    MS2_URL = os.getenv('MS2_URL', 'https://api.moysklad.ru')

    START_SYNC_DATE = os.getenv('START_SYNC_DATE', '2025-02-20 23:00:00')


class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
