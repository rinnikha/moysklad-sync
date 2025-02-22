import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler
import json

from flask_talisman import Talisman

from .sync.client import MoySkladClient

db = SQLAlchemy()

login_manager = LoginManager()

scheduler = BackgroundScheduler()


def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object('app.config.Config')

    app.ms1_client = MoySkladClient(
        api_token=app.config['MS1_TOKEN'],
        api_url=app.config['MS1_URL']
    )
    
    app.ms2_client = MoySkladClient(
        api_token=app.config['MS2_TOKEN'],
        api_url=app.config['MS2_URL']
    )

    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    
    # Initialize extensions
    db.init_app(app)

    Talisman(app, content_security_policy={
        'default-src': "'self'",
        'style-src': [
            "'self'",
            "'unsafe-inline'",  # For Bootstrap
            'https://stackpath.bootstrapcdn.com'
        ],
        'script-src': [
            "'self'",
            "'unsafe-inline'",  # For jQuery
            'https://code.jquery.com',
            'https://cdn.jsdelivr.net'
        ]
    })

    @app.template_filter('fromjson')
    def fromjson_filter(s):
        if isinstance(s, dict):
            return s
        try:
            return json.loads(s)
        except (TypeError, json.JSONDecodeError):
            return {}
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Create tables
    with app.app_context():
        db.create_all()

    with app.app_context():
        from app.sync.scheduler import start_scheduler
        start_scheduler(app)
    
    return app