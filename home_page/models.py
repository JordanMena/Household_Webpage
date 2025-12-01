from datetime import datetime
from flask import current_app
from home_page import db, login_manager
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship("Post", backref='author', lazy=True)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=1800)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"


# https://overiq.com/flask-101/database-modelling-in-flask/ <- info on implementing relationships in databases
recipe_tags = db.Table('recipe_tags',
                 db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
                 db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True)
)


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text, nullable=False, default='No description')
    image_file = db.Column(db.String(30), nullable=False, default='default.jpg')
    ingredients = db.Column(db.Text, nullable=False)
    directions = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(20), nullable=True)
    url = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    _tags = db.relationship('Tag', secondary=recipe_tags, lazy='subquery', backref=db.backref('recipes', lazy=True))

    # Help from https://github.com/eugenkiss/Simblin for getting tags into the db
    def _set_tags(self, taglist):
        # Remove all previous tags
        self._tags = []
        for tag_name in taglist:
            self._tags.append(Tag.get_or_create(tag_name))

    def _get_tags(self):
        return self._tags

    tags = db.synonym("_tags", descriptor=property(_get_tags, _set_tags))


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    color = db.Column(db.String(20), nullable=False, default='primary')

    @classmethod
    def get_or_create(cls, name):
        """Only add tags to the database that don't exist yet. If tag already
        exists return a reference to the tag otherwise a new instance"""
        tag = cls.query.filter(cls.name == name).first()
        if not tag:
            tag = cls(name)
        return tag

    def __init__(self, name):
        self.name = name
