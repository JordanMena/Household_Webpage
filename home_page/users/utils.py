from PIL import Image
from flask import url_for, current_app
from flask_mail import Message
from home_page import mail
import secrets
import os


def save_profile_pic(form_picture):
    random_hex = secrets.token_hex(8)
    # _ is an unused variable by convention
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn


def save_recipe_photo(form_picture):
    random_hex = secrets.token_hex(8)
    # _ is an unused variable by convention
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/recipe_photos', picture_fn)
    i = Image.open(form_picture)
    i.save(picture_path)
    return picture_fn


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset for Flask Blog', sender='jsmena11@gmail.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password visit the following link:
{url_for('users.reset_token', token=token, _external=True)}

If you did not make this request then you can ignore this email.
'''
    mail.send(msg)


def paginate_list(list_to_paginate, current_page, per_page=10):
    # First check that current page is not out-of-bounds for per_page value
    list_count = len(list_to_paginate)
    page_count = list_count//per_page + 1 if list_count % per_page > 0 else 0
    if current_page > page_count:
        raise ValueError("Invalid page number")
    """
    Example
    21 recipes, per_page = 10
    [0:9]
    [10:19]
    [20:29]
    (don't get an index error if you try to slice through to past end of list in case where last page is only partial, 
    Python will only go up to the last item in list)
    """
    return list_to_paginate[(per_page*(current_page-1)):(per_page*current_page)-1], page_count


def iter_pages(current_page, page_count, left_edge=1, right_edge=1, left_current=2, right_current=2):
    """"
    Build page list for navigation.
    left_current and right_current given greater priority than left_edge or right_edge
    For example, if page_count=5, left_edge = 1, right_edge = 1, left_current = 3, and current page=5
    then we return [1, None, 3, 4, 5] and not [1, None, 5]
    """
    page_list = []
    page_tracker = 1
    if current_page > page_count:
        raise RuntimeError("Current page greater than page count")
    if left_edge < 1 or right_edge < 1 or right_current < 1 or left_current < 0:
        raise ValueError("Inputs too small to create navigable list")
    if page_count < 1:
        raise ValueError("Must have at least one page")
    # Start by inserting pages from left edge
    '''
    Start list at left_edge and work our way right
    '''
    for i in range(left_edge):
        # If we insert page_count pages we're done
        if page_tracker <= page_count:
            page_list.append(page_tracker)
            page_tracker += 1
        else:
            return page_list
    '''
    Now look at left_current. Don't have to worry about inserting more than page_count since
    current_page is guaranteed to be < page_count
    '''
    # Make sure we don't insert negative numbers or duplicate pages
    if (current_page - left_current) < page_tracker:
        left_current = current_page - page_tracker
    if (current_page - left_current) > page_tracker + 1:
        page_list.append(None)
    # Advance page_tracker to its new position
    page_tracker = current_page - left_current
    # Insert one extra to bring us to current
    for i in range(left_current+1):
        page_list.append(page_tracker)
        page_tracker += 1
    if page_tracker == page_count:
        return page_list
    '''
    Now insert up to right_current or end of list.
    '''
    for i in range(right_current):
        if page_tracker <= page_count:
            page_list.append(page_tracker)
            page_tracker += 1
        else:
            return page_list
    '''
    Finish with right edge
    '''
    # Same as above, avoid duplicates  and insert discontinuity if need be
    if page_count - right_edge < page_tracker:
        right_edge = page_count - page_tracker
    if page_count - right_edge > page_tracker + 1:
        page_list.append(None)
    page_tracker = page_count - right_edge + 1
    for i in range(right_edge):
        if page_tracker <= page_count:
            page_list.append(page_tracker)
            page_tracker +=1
    # Should be at end now
    return page_list
