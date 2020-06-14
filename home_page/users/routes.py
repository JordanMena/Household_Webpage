from flask import render_template, url_for, flash, redirect, request, Blueprint, g
from flask_login import login_user, current_user, logout_user, login_required
from home_page import bcrypt, db
from home_page.models import User, Post, Recipe, Tag
from home_page.users.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                                   RequestResetForm, ResetPasswordForm, AddRecipeForm)
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
    form = AddRecipeForm()
    if form.validate_on_submit():
        recipe = Recipe(name=form.name.data, description=form.description.data,
                        ingredients=form.ingredients.data, directions=form.directions.data,
                        source=form.source.data, notes=form.notes.data,
                        url=form.url.data)
        recipe.tags = form.tags.data.copy()
        if form.picture.data:
            picture_file = save_recipe_photo(form.picture.data)
            recipe.image_file = picture_file
        db.session.add(recipe)
        db.session.commit()
        flash('Your recipe has been added!', 'success')
        return redirect(url_for('users.recipes'))
    return render_template('add_recipe.html', title='New Recipe',
                           form=form, legend='New Recipe')


@users.route("/recipe/<int:recipe_id>/update", methods=['GET', 'POST'])
def update_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    form = AddRecipeForm()
    if form.validate_on_submit():
        recipe.name = form.name.data
        recipe.description = form.description.data
        recipe.ingredients = form.ingredients.data
        recipe.directions = form.directions.data
        recipe.source = form.source.data
        recipe.notes = form.notes.data
        recipe.url = form.url.data
        recipe.tags = form.tags.data.copy()
        if form.picture.data:
            picture_file = save_recipe_photo(form.picture.data)
            recipe.image_file = picture_file
        db.session.commit()
        flash("Recipe has been updated!", 'success')
        return redirect(url_for('users.recipe', recipe_id=recipe.id))
    elif request.method == 'GET':
        form.name.data = recipe.name
        form.description.data = recipe.description
        form.ingredients.data = recipe.ingredients
        form.directions.data = recipe.directions
        form.notes.data = recipe.notes
        form.source.data = recipe.source
        form.tags.data = recipe.tags
    return render_template('add_recipe.html', title='Update Recipe',
                           form=form, legend='Update Recipe')


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


@users.before_app_request
def get_recipe_tags():
    g.recipe_tags = Tag.query.order_by(Tag.id)
