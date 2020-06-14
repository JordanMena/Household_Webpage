from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from home_page.config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'
mail = Mail()

# Need to import after app initialization since route.py depends on app

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    from home_page.users.routes import users
    from home_page.posts.routes import posts
    from home_page.main.routes import main
    from home_page.errors.handlers import errors

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager .init_app(app)
    mail.init_app(app)

    app.register_blueprint(users)
    app.register_blueprint(posts)
    app.register_blueprint(main)
    app.register_blueprint(errors)

    return app
