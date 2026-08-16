import calendar
from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from home_page import db
from home_page.maintenance.forms import (
    ArchiveTaskForm, MaintenanceCompletionForm, MaintenanceTaskForm
)
from home_page.maintenance.scheduling import next_future_due
from home_page.models import MaintenanceCompletion, MaintenanceTask


maintenance = Blueprint('maintenance', __name__, url_prefix='/maintenance')


@maintenance.route('/')
@login_required
def index():
    today = date.today()
    active_tasks = MaintenanceTask.query.filter_by(is_active=True).order_by(
        MaintenanceTask.next_due_date.is_(None), MaintenanceTask.next_due_date
    ).all()
    overdue_tasks = [
        task for task in active_tasks
        if task.next_due_date and task.next_due_date < today
    ]
    upcoming_tasks = [
        task for task in active_tasks
        if task.next_due_date and task.next_due_date >= today
    ]
    inactive_tasks = MaintenanceTask.query.filter_by(is_active=False).order_by(
        MaintenanceTask.name
    ).all()
    completed_one_offs = MaintenanceTask.query.filter_by(
        is_active=True, recurrence_unit='once', next_due_date=None
    ).order_by(MaintenanceTask.name).all()
    return render_template(
        'maintenance/index.html',
        title='Home Maintenance',
        overdue_tasks=overdue_tasks,
        upcoming_tasks=upcoming_tasks,
        inactive_tasks=inactive_tasks,
        completed_one_offs=completed_one_offs,
        today=today,
    )


@maintenance.route('/new', methods=['GET', 'POST'])
@login_required
def new_task():
    form = MaintenanceTaskForm()
    if form.validate_on_submit():
        interval = form.recurrence_interval.data or 1
        task = MaintenanceTask(
            name=form.name.data.strip(),
            description=form.description.data,
            first_due_date=form.first_due_date.data,
            next_due_date=form.first_due_date.data,
            recurrence_interval=interval,
            recurrence_unit=form.recurrence_unit.data,
            is_active=form.is_active.data,
        )
        db.session.add(task)
        db.session.commit()
        flash('Maintenance task added.', 'success')
        return redirect(url_for('maintenance.task_detail', task_id=task.id))
    if request.method == 'GET':
        form.recurrence_interval.data = 1
        form.is_active.data = True
    return render_template(
        'maintenance/task_form.html', title='Add Maintenance Task', form=form,
        legend='Add maintenance task'
    )


@maintenance.route('/<int:task_id>')
@login_required
def task_detail(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    completions = MaintenanceCompletion.query.filter_by(task_id=task.id).order_by(
        MaintenanceCompletion.completed_date.desc(),
        MaintenanceCompletion.recorded_at.desc(),
    ).all()
    return render_template(
        'maintenance/task_detail.html', title=task.name, task=task,
        completions=completions, today=date.today(), archive_form=ArchiveTaskForm()
    )


@maintenance.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    form = MaintenanceTaskForm()
    if form.validate_on_submit():
        interval = form.recurrence_interval.data or 1
        schedule_changed = (
            task.first_due_date != form.first_due_date.data
            or task.recurrence_interval != interval
            or task.recurrence_unit != form.recurrence_unit.data
        )
        task.name = form.name.data.strip()
        task.description = form.description.data
        task.first_due_date = form.first_due_date.data
        task.recurrence_interval = interval
        task.recurrence_unit = form.recurrence_unit.data
        task.is_active = form.is_active.data
        if schedule_changed:
            task.next_due_date = form.first_due_date.data
        db.session.commit()
        flash('Maintenance task updated.', 'success')
        return redirect(url_for('maintenance.task_detail', task_id=task.id))
    if request.method == 'GET':
        form.name.data = task.name
        form.description.data = task.description
        form.first_due_date.data = task.first_due_date
        form.recurrence_interval.data = task.recurrence_interval
        form.recurrence_unit.data = task.recurrence_unit
        form.is_active.data = task.is_active
    return render_template(
        'maintenance/task_form.html', title=f'Edit {task.name}', form=form,
        legend='Edit maintenance task', task=task
    )


@maintenance.route('/<int:task_id>/complete', methods=['GET', 'POST'])
@login_required
def complete_task(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    if not task.is_active:
        flash('Reactivate this task before completing it.', 'warning')
        return redirect(url_for('maintenance.task_detail', task_id=task.id))
    if task.next_due_date is None:
        flash('This one-off task is already complete.', 'info')
        return redirect(url_for('maintenance.task_detail', task_id=task.id))

    form = MaintenanceCompletionForm()
    if form.validate_on_submit():
        completion = MaintenanceCompletion(
            task=task,
            scheduled_due_date=task.next_due_date,
            completed_date=form.completed_date.data,
            notes=form.notes.data,
            completed_by=current_user,
        )
        db.session.add(completion)
        task.next_due_date = next_future_due(
            current_due=task.next_due_date,
            interval=task.recurrence_interval,
            unit=task.recurrence_unit,
            anchor_date=task.first_due_date,
            today=date.today(),
        )
        db.session.commit()
        if task.next_due_date:
            flash(
                f'Task completed. Next due {task.next_due_date:%B %d, %Y}.',
                'success',
            )
        else:
            flash('One-off task completed.', 'success')
        return redirect(url_for('maintenance.task_detail', task_id=task.id))
    return render_template(
        'maintenance/complete_task.html', title=f'Complete {task.name}',
        form=form, task=task
    )


@maintenance.route('/<int:task_id>/archive', methods=['POST'])
@login_required
def archive_task(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    form = ArchiveTaskForm()
    if not form.validate_on_submit():
        abort(400)
    task.is_active = False
    db.session.commit()
    flash('Maintenance task archived. Its history has been retained.', 'success')
    return redirect(url_for('maintenance.index'))


@maintenance.route('/calendar')
@login_required
def calendar_view():
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    if year < 1 or year > 9999 or month < 1 or month > 12:
        flash('Invalid calendar month.', 'warning')
        return redirect(url_for('maintenance.calendar_view'))

    month_calendar = calendar.Calendar(firstweekday=6)
    weeks = month_calendar.monthdatescalendar(year, month)
    grid_start, grid_end = weeks[0][0], weeks[-1][-1]
    tasks = MaintenanceTask.query.filter(
        MaintenanceTask.is_active.is_(True),
        MaintenanceTask.next_due_date.isnot(None),
        MaintenanceTask.next_due_date >= grid_start,
        MaintenanceTask.next_due_date <= grid_end,
    ).order_by(MaintenanceTask.next_due_date, MaintenanceTask.name).all()
    tasks_by_date = {}
    for task in tasks:
        tasks_by_date.setdefault(task.next_due_date, []).append(task)
    overdue_count = MaintenanceTask.query.filter(
        MaintenanceTask.is_active.is_(True),
        MaintenanceTask.next_due_date < today,
    ).count()

    if month == 1:
        previous_year, previous_month = year - 1, 12
    else:
        previous_year, previous_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    return render_template(
        'maintenance/calendar.html', title='Maintenance Calendar',
        weeks=weeks, tasks_by_date=tasks_by_date, today=today,
        month=month, year=year, month_name=calendar.month_name[month],
        previous_year=previous_year, previous_month=previous_month,
        next_year=next_year, next_month=next_month,
        overdue_count=overdue_count,
    )
