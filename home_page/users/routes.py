from flask import render_template, url_for, flash, redirect, request, Blueprint, g, jsonify
from werkzeug.datastructures import MultiDict
from home_page.users.recipe_data import decode_import, IMPORT_PROMPT, ingredients_text, parse_ingredients, parse_steps, normalized_url
from flask_login import login_user, current_user, logout_user, login_required
from home_page import bcrypt, db
from home_page.models import User, Post, Recipe, Tag
from home_page.users.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                                   RequestResetForm, ResetPasswordForm, AddRecipeForm, AddTagForm, RecipeImportForm)
from home_page.users.utils import (save_profile_pic, save_recipe_photo, send_reset_email,
                                   paginate_list, iter_pages)

users = Blueprint('users', __name__)


@users.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created! You can now log in, {form.username.data}!', 'success')
        return redirect(url_for('users.login'))
    return render_template('register.html', title='Register', form=form)


@users.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Login unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@users.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@users.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_profile_pic(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('You account has been updated', 'success')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)


@users.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user) \
        .order_by(Post.date_posted.desc()) \
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)


@users.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('users.login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@users.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('users.reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash(f'Your password has been updated! You can now log in!', 'success')
        return redirect(url_for('users.login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@users.route("/recipe/<int:recipe_id>")
def recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    return render_template('recipe.html', title=recipe.name, recipe=recipe)


@users.route("/recipes")
def recipes():
    page = request.args.get('page', 1, type=int)
    posted_recipes = Recipe.query.order_by(Recipe.id).paginate(page=page, per_page=5)
    return render_template('recipes.html', recipes=posted_recipes, title='Recipes')


@users.route("/recipes/new", methods=['GET', 'POST'])
def new_recipe():
    return recipe_editor()


@users.route("/recipe/<int:recipe_id>/update", methods=['GET', 'POST'])
def update_recipe(recipe_id):
    return recipe_editor(Recipe.query.get_or_404(recipe_id))


def matching_recipes(url, exclude_id=None):
    if not url:
        return []
    target = normalized_url(url)
    return [item for item in Recipe.query.filter(Recipe.url.isnot(None)).all()
            if item.id != exclude_id and normalized_url(item.url) == target]


@users.route('/recipes/import', methods=['POST'])
def import_recipe():
    import_form = RecipeImportForm()
    if not import_form.validate_on_submit():
        return jsonify(errors=import_form.errors), 400
    try:
        values = decode_import(import_form.recipe_json.data)
    except ValueError as error:
        return jsonify(errors={'recipe_json': [str(error)]}), 400
    values['csrf_token'] = request.form.get('csrf_token', '')
    form = AddRecipeForm(MultiDict(values))
    if not form.validate():
        return jsonify(errors=form.errors), 400
    values.pop('csrf_token', None)
    values['tags'] = form.tags.data
    duplicates = matching_recipes(values['url'], request.form.get('recipe_id', type=int))
    return jsonify(values=values, duplicates=[{
        'name': item.name, 'url': url_for('users.recipe', recipe_id=item.id)
    } for item in duplicates])


def recipe_editor(recipe=None):
    editing = recipe is not None
    form = AddRecipeForm()
    duplicates = []
    if form.validate_on_submit():
        duplicates = matching_recipes(form.url.data.strip(), recipe.id if editing else None)
        if not duplicates or request.form.get('allow_duplicate') == 'yes':
            recipe = recipe if editing else Recipe()
            for key in ('name', 'description', 'notes', 'source', 'url', 'servings'):
                setattr(recipe, key, (getattr(form, key).data or '').strip())
            for key in ('prep_time_minutes', 'cook_time_minutes'):
                setattr(recipe, key, getattr(form, key).data)
            recipe.ingredient_groups = parse_ingredients(form.ingredients.data)
            recipe.direction_steps = parse_steps(form.directions.data)
            recipe.ingredients = '|'.join(item for group in recipe.ingredient_groups for item in group['ingredients'])
            recipe.directions = '\n\n'.join(recipe.direction_steps)
            recipe.tags = form.tags.data.copy()
            if form.picture.data:
                recipe.image_file = save_recipe_photo(form.picture.data)
            db.session.add(recipe)
            db.session.commit()
            flash('Your recipe has been saved!', 'success')
            return redirect(url_for('users.recipe', recipe_id=recipe.id))
    elif request.method == 'GET' and editing:
        for key in ('name', 'description', 'notes', 'source', 'url', 'servings', 'prep_time_minutes', 'cook_time_minutes'):
            getattr(form, key).data = getattr(recipe, key)
        form.ingredients.data = (ingredients_text(recipe.ingredient_groups) if recipe.ingredient_groups
                                 else recipe.ingredients.replace('|', '\n'))
        form.directions.data = '\n\n'.join(recipe.direction_steps) if recipe.direction_steps else recipe.directions
        form.tags.data = [tag.name for tag in recipe.tags]
    tags = Tag.query.order_by(Tag.name).all()
    known_names = {tag.name for tag in tags}
    tags += [dict(name=name, color='primary') for name in (form.tags.data or []) if name not in known_names]
    title = 'Edit recipe' if editing else 'New recipe'
    return render_template('add_recipe.html', title=title, form=form, legend=title,
                           all_tags=tags, recipe=recipe, duplicates=duplicates, import_prompt=IMPORT_PROMPT,
                           import_json=request.form.get('recipe_json', ''))


@users.route("/recipe/<int:recipe_id>/delete", methods=['POST'])
def delete_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    flash('Your recipe has been deleted.', 'warning')
    return redirect(url_for('users.recipes'))


@users.route("/tag/<int:tag_id>")
def tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    page = request.args.get('page', 1, type=int)
    recipes, page_count = paginate_list(tag.recipes, page, per_page=10)
    page_nums = iter_pages(page, page_count, left_edge=1, right_edge=1, left_current=2, right_current=2)
    return render_template('tag.html', title=tag.name, tag=tag, recipes=recipes,
                           page_list=page_nums, current_page=page)


@users.route("/combine_tags/<string:tag1>_and_<string:tag2>")
def combine_tags(tag1, tag2):
    combined_tags = [tag1, tag2]
    recipes = db.session.query(Recipe)
    for tag in combined_tags:
        recipes = recipes.filter(Recipe.tags.any(Tag.name.startswith(tag)))
    print(recipes)
    return render_template('combine_tags.html', recipes=recipes, tag1=tag1, tag2=tag2)


@users.route("/manage_tags", methods=['GET', 'POST'])
@login_required
def manage_tags():
    form = AddTagForm()
    if form.validate_on_submit():
        tag = Tag.get_or_create(form.name.data.lower())
        db.session.add(tag)
        db.session.commit()
        flash('Tag added!', 'success')
        return redirect(url_for('users.manage_tags'))
    tags = Tag.query.order_by(Tag.name).all()
    return render_template('manage_tags.html', title='Manage Tags', tags=tags, form=form)


@users.route("/tag/<int:tag_id>/delete", methods=['POST'])
@login_required
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    flash('Tag has been deleted.', 'success')
    return redirect(url_for('users.manage_tags'))


@users.route("/tag/<int:tag_id>/update_color", methods=['POST'])
@login_required
def update_tag_color(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    new_color = request.form.get('color')
    if new_color in ['primary', 'secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark']:
        tag.color = new_color
        db.session.commit()
        flash('Tag color updated!', 'success')
    else:
        flash('Invalid color selected.', 'danger')
    return redirect(url_for('users.manage_tags'))


# Make the recipe tags always available through g since they are required in the routeless recipes_layout.html template
@users.before_app_request
def get_recipe_tags():
    g.recipe_tags = Tag.query.order_by(Tag.id)
