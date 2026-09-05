from datetime import date

from flask_wtf import FlaskForm
from wtforms import DecimalField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError


from home_page.freezer.categories import CATEGORIES, DEFAULT_CATEGORY


class FreezerItemForm(FlaskForm):
    category = SelectField(
        "Category", choices=[(name, name) for name in CATEGORIES],
        default=DEFAULT_CATEGORY, validators=[DataRequired()],
    )
    name = StringField('Item name', validators=[DataRequired(), Length(max=120)])
    description = TextAreaField('Description or notes', validators=[Optional()])
    freezer_location = SelectField(
        'Freezer',
        choices=[
            ('upstairs', 'Upstairs fridge freezer'),
            ('basement', 'Basement deep freeze'),
        ],
        validators=[DataRequired()],
    )
    quantity = DecimalField(
        'Quantity', places=2,
        validators=[Optional(), NumberRange(min=0.01, max=999999)],
    )
    unit = StringField(
        'Units', validators=[Optional(), Length(max=30)]
    )
    date_added = DateField(
        'Date added', validators=[DataRequired()], format='%Y-%m-%d', default=date.today
    )
    warning_months = IntegerField(
        'Warn after this many months',
        validators=[Optional(), NumberRange(min=1, max=120)],
    )
    submit = SubmitField('Save item')

    def validate_date_added(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('Date added cannot be in the future.')


class DeleteFreezerItemForm(FlaskForm):
    submit = SubmitField('Remove item')
