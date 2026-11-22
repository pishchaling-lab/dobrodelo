import os
from flask import Flask
from flask_login import LoginManager
from sqlalchemy import text
from app.config import Config
from app.models import db, User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Инициализация базы данных и авторизации
    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        # Register Blueprints
        from app.routes.auth import auth_bp
        from app.routes.main import main_bp
        from app.routes.volunteer import volunteer_bp
        from app.routes.coordinator import coordinator_bp
        from app.routes.admin import admin_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(volunteer_bp, url_prefix='/volunteer')
        app.register_blueprint(coordinator_bp, url_prefix='/coordinator')
        app.register_blueprint(admin_bp, url_prefix='/admin')

        # Create all tables if they don't exist
        db.create_all()

    return app
