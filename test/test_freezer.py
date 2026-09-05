from datetime import date, timedelta
from unittest import TestCase

from home_page import bcrypt, create_app, db
from home_page.freezer.aging import add_calendar_months, is_old_item, warning_date
from home_page.models import FreezerItem, User


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


class TestFreezerAging(TestCase):
    def test_calendar_month_math_handles_short_months(self):
        self.assertEqual(
            add_calendar_months(date(2026, 1, 31), 1),
            date(2026, 2, 28),
        )

    def test_default_and_item_specific_warning_dates(self):
        default_item = FreezerItem(
            name='Soup', freezer_location='upstairs', date_added=date(2026, 1, 15)
        )
        custom_item = FreezerItem(
            name='Bread', freezer_location='upstairs', date_added=date(2026, 1, 15),
            warning_months=2,
        )
        self.assertEqual(warning_date(default_item), date(2026, 6, 15))
        self.assertEqual(warning_date(custom_item), date(2026, 3, 15))
        self.assertFalse(is_old_item(default_item, date(2026, 6, 14)))
        self.assertTrue(is_old_item(default_item, date(2026, 6, 15)))


class TestFreezerRoutes(TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        user = User(
            username='homeowner', email='homeowner@example.com',
            password=bcrypt.generate_password_hash('password').decode('utf-8'),
        )
        db.session.add(user)
        db.session.commit()
        with self.client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_create_edit_move_and_delete_item(self):
        response = self.client.post(
            '/freezer/new',
            data={
                'name': 'Chicken thighs',
                'description': 'Individually wrapped',
                'freezer_location': 'basement',
                'quantity': '6',
                'unit': 'pieces',
                'date_added': date.today().isoformat(),
                'warning_months': '',
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Chicken thighs', response.data)
        self.assertIn(b'6 pieces', response.data)
        item = FreezerItem.query.one()
        self.assertEqual(item.freezer_location, 'basement')
        self.assertIsNone(item.warning_months)

        response = self.client.post(
            f'/freezer/{item.id}/edit',
            data={
                'name': 'Chicken thighs',
                'description': 'Individually wrapped',
                'freezer_location': 'upstairs',
                'quantity': '4.5',
                'unit': 'pieces',
                'date_added': date.today().isoformat(),
                'warning_months': '3',
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(item.freezer_location, 'upstairs')
        self.assertEqual(item.quantity, 4.5)
        self.assertEqual(item.warning_months, 3)
        self.assertIn(b'4.5 pieces', response.data)

        response = self.client.post(
            f'/freezer/{item.id}/delete', follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'removed from the freezer inventory', response.data)
        self.assertEqual(FreezerItem.query.count(), 0)

    def test_search_and_age_sorting_cover_both_freezers(self):
        older = FreezerItem(
            name='Tomato soup', description='Red container',
            freezer_location='upstairs', date_added=date.today() - timedelta(days=30),
        )
        newer = FreezerItem(
            name='Tomato sauce', description='Glass-safe container',
            freezer_location='basement', date_added=date.today() - timedelta(days=5),
        )
        unrelated = FreezerItem(
            name='Blueberries', freezer_location='basement', date_added=date.today()
        )
        db.session.add_all([newer, unrelated, older])
        db.session.commit()

        response = self.client.get('/freezer/?q=tomato&sort=oldest')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Tomato soup', response.data)
        self.assertIn(b'Tomato sauce', response.data)
        self.assertNotIn(b'Blueberries', response.data)
        self.assertLess(
            response.data.index(b'Tomato soup'),
            response.data.index(b'Tomato sauce'),
        )

    def test_dashboard_shows_only_items_past_their_threshold(self):
        old_item = FreezerItem(
            name='Old chili', freezer_location='basement',
            date_added=date.today() - timedelta(days=200),
        )
        custom_fresh_item = FreezerItem(
            name='Long-term berries', freezer_location='basement',
            date_added=date.today() - timedelta(days=200), warning_months=12,
        )
        db.session.add_all([old_item, custom_fresh_item])
        db.session.commit()

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Freezer items to use soon', response.data)
        self.assertIn(b'Old chili', response.data)
        self.assertNotIn(b'Long-term berries', response.data)

    def test_future_date_is_rejected(self):
        response = self.client.post(
            '/freezer/new',
            data={
                'name': 'Tomorrow food',
                'freezer_location': 'upstairs',
                'quantity': '',
                'unit': '',
                'date_added': (date.today() + timedelta(days=1)).isoformat(),
                'warning_months': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'cannot be in the future', response.data)
        self.assertEqual(FreezerItem.query.count(), 0)

    def test_category_defaults_validation_and_move(self):
        data = dict(name='Category test', freezer_location='upstairs',
                    date_added=date.today().isoformat())
        self.client.post('/freezer/new', data=data)
        item = FreezerItem.query.one()
        self.assertEqual(item.category, 'Misc')
        for category in ('Meal Prep', 'Single Meal', 'Leftovers', 'Carbs',
                         'Fruits/Veg/Spices', 'Desserts', 'Misc'):
            data.update(category=category, freezer_location='basement')
            self.client.post(f'/freezer/{item.id}/edit', data=data)
            self.assertEqual(item.category, category)
            self.assertEqual(item.freezer_location, 'basement')
            response = self.client.get(f'/freezer/{item.id}/edit')
            self.assertIn(('selected value="' + category + '"').encode(), response.data)
        data['category'] = 'Invalid'
        response = self.client.post(f'/freezer/{item.id}/edit', data=data)
        self.assertIn(b'Not a valid choice', response.data)
        self.assertEqual(item.category, 'Misc')

    def test_category_and_location_filters_combine_with_search(self):
        for name, category, location in (
            ('Soup batch', 'Meal Prep', 'upstairs'),
            ('Soup portion', 'Meal Prep', 'basement'),
            ('Soup leftover', 'Leftovers', 'basement'),
            ('Pasta batch', 'Meal Prep', 'basement'),
        ):
            db.session.add(FreezerItem(name=name, category=category,
                                      freezer_location=location, date_added=date.today()))
        db.session.commit()
        response = self.client.get('/freezer/?category=Meal+Prep')
        self.assertIn(b'Soup batch', response.data)
        self.assertIn(b'Soup portion', response.data)
        self.assertNotIn(b'Soup leftover', response.data)
        response = self.client.get('/freezer/?category=Meal+Prep&location=basement&q=Soup')
        self.assertIn(b'Soup portion', response.data)
        for excluded in (b'Soup batch', b'Soup leftover', b'Pasta batch'):
            self.assertNotIn(excluded, response.data)

    def test_migration_backfills_existing_items_and_can_repeat(self):
        from update_db import update_db
        db.session.remove()
        with db.engine.begin() as connection:
            connection.execute('DROP TABLE freezer_item')
            connection.execute("CREATE TABLE freezer_item (id INTEGER PRIMARY KEY, name TEXT)")
            connection.execute("INSERT INTO freezer_item (name) VALUES ('Existing food')")
        update_db()
        update_db()
        with db.engine.connect() as connection:
            row = connection.execute('SELECT name, category FROM freezer_item').fetchone()
            self.assertEqual(tuple(row), ('Existing food', 'Misc'))
