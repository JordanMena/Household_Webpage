from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from home_page.models import User
from flask_login import current_user


class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def  validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken.')

    def  validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already belongs to a registered user.')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=6)])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username already taken.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email already belongs to a registered user.')


class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def  validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. You must register first.')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


# Taken almost unmodified from https://gist.github.com/M0r13n/71655c53b2fbf41dc1db8412978bcbf9
class TagListField(StringField):
    """Stringfield for a list of separated tags"""

    def __init__(self, label='', validators=None, remove_duplicates=True, to_lowercase=True, separator=' ', **kwargs):
        """
        Construct a new field.
        :param label: The label of the field.
        :param validators: A sequence of validators to call when validate is called.
        :param remove_duplicates: Remove duplicates in a case insensitive manner.
        :param to_lowercase: Cast all values to lowercase.
        :param separator: The separator that splits the individual tags.
        """
        super(TagListField, self).__init__(label, validators, **kwargs)
        self.remove_duplicates = remove_duplicates
        self.to_lowercase = to_lowercase
        self.separator = separator
        self.data = []

    def _value(self):
        if self.data:
            names = []
            for tag in self.data:
                if isinstance(tag, str):
                    names.append(tag)
                elif hasattr(tag, 'name'):
                    names.append(tag.name)
                else:
                    names.append(str(tag))
            return u'|'.join(names)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip() for x in valuelist[0].split(self.separator)]
            if self.remove_duplicates:
                self.data = list(self._remove_duplicates(self.data))
            if self.to_lowercase:
                self.data = [x.lower() for x in self.data]

    @classmethod
    def _remove_duplicates(cls, seq):
        """Remove duplicates in a case insensitive, but case preserving manner"""
        d = {}
        for item in seq:
            if item.lower() not in d:
                d[item.lower()] = True
                yield item


class AddRecipeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=30, message="Shorter name please.")])
    description = TextAreaField('Description', validators=[])
    ingredients = TextAreaField('Ingredients', validators=[DataRequired()])
    directions = TextAreaField('Directions', validators=[DataRequired()])
    picture = FileField('Picture', validators=[FileAllowed(['jpg', 'png'])])
    notes = TextAreaField('Notes', validators=[])
    source = StringField('Source', validators=[DataRequired(), Length(max=20, message="Too long.")])
    url = StringField('URL', validators=[])
    tags = TagListField('Tags', separator='|', validators=[])
    submit = SubmitField('Post Recipe')


class AddTagForm(FlaskForm):
    name = StringField('Tag Name', validators=[DataRequired(), Length(max=20)])
    submit = SubmitField('Add Tag')

