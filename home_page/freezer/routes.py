from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_

from home_page import db
from home_page.freezer.aging import is_old_item
from home_page.freezer.forms import DeleteFreezerItemForm, FreezerItemForm
from home_page.models import FreezerItem


freezer = Blueprint('freezer', __name__, url_prefix='/freezer')


@freezer.route('/')
@login_required
def inventory():
    search = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'oldest')
    query = FreezerItem.query
    if search:
        pattern = f'%{search}%'
        query = query.filter(or_(
            FreezerItem.name.ilike(pattern),
            FreezerItem.description.ilike(pattern),
            FreezerItem.unit.ilike(pattern),
        ))

    sort_options = {
        'oldest': (FreezerItem.date_added.asc(), FreezerItem.name.asc()),
        'newest': (FreezerItem.date_added.desc(), FreezerItem.name.asc()),
        'name': (FreezerItem.name.asc(), FreezerItem.date_added.asc()),
    }
    if sort not in sort_options:
        sort = 'oldest'
    items = query.order_by(*sort_options[sort]).all()
    upstairs_items = [item for item in items if item.freezer_location == 'upstairs']
    basement_items = [item for item in items if item.freezer_location == 'basement']
    today = date.today()
    old_item_ids = {item.id for item in items if is_old_item(item, today)}

    return render_template(
        'freezer/inventory.html', title='Freezer Inventory',
        upstairs_items=upstairs_items, basement_items=basement_items,
        search=search, sort=sort, old_item_ids=old_item_ids,
        delete_form=DeleteFreezerItemForm(), today=today,
    )


@freezer.route('/new', methods=['GET', 'POST'])
@login_required
def new_item():
    form = FreezerItemForm()
    if form.validate_on_submit():
        item = FreezerItem(
            name=form.name.data.strip(),
            description=form.description.data,
            freezer_location=form.freezer_location.data,
            quantity=float(form.quantity.data) if form.quantity.data is not None else None,
            unit=form.unit.data.strip() if form.unit.data else None,
            date_added=form.date_added.data,
            warning_months=form.warning_months.data,
        )
        db.session.add(item)
        db.session.commit()
        flash(f'{item.name} added to the freezer inventory.', 'success')
        return redirect(url_for('freezer.inventory'))
    return render_template(
        'freezer/item_form.html', title='Add Freezer Item', form=form,
        legend='Add freezer item'
    )


@freezer.route('/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = FreezerItem.query.get_or_404(item_id)
    form = FreezerItemForm()
    if form.validate_on_submit():
        item.name = form.name.data.strip()
        item.description = form.description.data
        item.freezer_location = form.freezer_location.data
        item.quantity = float(form.quantity.data) if form.quantity.data is not None else None
        item.unit = form.unit.data.strip() if form.unit.data else None
        item.date_added = form.date_added.data
        item.warning_months = form.warning_months.data
        db.session.commit()
        flash(f'{item.name} updated.', 'success')
        return redirect(url_for('freezer.inventory'))
    if request.method == 'GET':
        form.name.data = item.name
        form.description.data = item.description
        form.freezer_location.data = item.freezer_location
        form.quantity.data = item.quantity
        form.unit.data = item.unit
        form.date_added.data = item.date_added
        form.warning_months.data = item.warning_months
    return render_template(
        'freezer/item_form.html', title=f'Edit {item.name}', form=form,
        legend='Edit freezer item', item=item,
        delete_form=DeleteFreezerItemForm(),
    )


@freezer.route('/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    item = FreezerItem.query.get_or_404(item_id)
    form = DeleteFreezerItemForm()
    if not form.validate_on_submit():
        abort(400)
    name = item.name
    db.session.delete(item)
    db.session.commit()
    flash(f'{name} removed from the freezer inventory.', 'success')
    return redirect(url_for('freezer.inventory'))
