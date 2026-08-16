from datetime import date, timedelta

from flask import render_template, Blueprint
from flask_login import current_user

from home_page.models import MaintenanceTask

main = Blueprint('main', __name__)

@main.route("/")
@main.route("/home")
def home():
    overdue_tasks = []
    due_soon_tasks = []
    today = date.today()
    if current_user.is_authenticated:
        overdue_tasks = MaintenanceTask.query.filter(
            MaintenanceTask.is_active.is_(True),
            MaintenanceTask.next_due_date < today,
        ).order_by(MaintenanceTask.next_due_date).all()
        due_soon_tasks = MaintenanceTask.query.filter(
            MaintenanceTask.is_active.is_(True),
            MaintenanceTask.next_due_date >= today,
            MaintenanceTask.next_due_date <= today + timedelta(days=30),
        ).order_by(MaintenanceTask.next_due_date).all()
    return render_template(
        'home.html', overdue_tasks=overdue_tasks,
        due_soon_tasks=due_soon_tasks, today=today,
        title='The Mena-Kelly Household'
    )


@main.route("/about")
def about():
    return render_template('about.html', title='About')

