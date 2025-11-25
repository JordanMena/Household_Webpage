import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cde00bf9b89d81a8e34d7b2eb9f8bfbf'
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or 'sqlite:///' + os.path.join(basedir, 'site.db')
    MAIL_SERVER = 'smpt.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
