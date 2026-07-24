import os
import json


config_path = os.environ.get('HOUSEHOLD_CONFIG', '/etc/config.json')
try:
    with open(config_path) as config_file:
        file_config = json.load(config_file)
except FileNotFoundError:
    file_config = {}


class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))
    SECRET_KEY = os.environ.get('SECRET_KEY') or file_config.get('SECRET_KEY') or 'development-only-key'
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('SQLALCHEMY_DATABASE_URI')
        or file_config.get('SQLALCHEMY_DATABASE_URI')
        or 'sqlite:///' + os.path.join(basedir, 'site.db')
    )
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or file_config.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or file_config.get('MAIL_PASSWORD')
