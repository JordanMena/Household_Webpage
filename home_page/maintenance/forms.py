from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
)
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError


class MaintenanceTaskForm(FlaskForm):
    name = StringField(
        'Task name', validators=[DataRequired(), Length(max=120)]
    )
    description = TextAreaField('Description or instructions', validators=[Optional()])
    first_due_date = DateField(
        'First due date', validators=[DataRequired()], format='%Y-%m-%d'
    )
    recurrence_interval = IntegerField(
        'Repeat every', validators=[Optional(), NumberRange(min=1, max=999)]
    )
    recurrence_unit = SelectField(
        'Period',
        choices=[
            ('once', 'Do not repeat'),
            ('day', 'Day(s)'),
            ('week', 'Week(s)'),
            ('month', 'Month(s)'),
            ('year', 'Year(s)'),
        ],
        validators=[DataRequired()],
    )
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save task')

    def validate_recurrence_interval(self, field):
        if self.recurrence_unit.data != 'once' and field.data is None:
            raise ValidationError('Enter how often this task repeats.')


class MaintenanceCompletionForm(FlaskForm):
    completed_date = DateField(
        'Completion date',
        validators=[DataRequired()],
        format='%Y-%m-%d',
        default=date.today,
    )
    notes = TextAreaField('Notes (optional)', validators=[Optional()])
    submit = SubmitField('Mark complete')

    def validate_completed_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('Completion date cannot be in the future.')


class ArchiveTaskForm(FlaskForm):
    submit = SubmitField('Archive task')
