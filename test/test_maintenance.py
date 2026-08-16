from datetime import date, timedelta
from unittest import TestCase

from home_page import bcrypt, create_app, db
from home_page.maintenance.scheduling import next_future_due, next_scheduled_date
from home_page.models import MaintenanceCompletion, MaintenanceTask, User


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


class TestMaintenanceScheduling(TestCase):
    def test_month_end_schedule_keeps_anchor_day(self):
        anchor = date(2025, 1, 31)
        february = next_scheduled_date(anchor, 1, 'month', anchor)
        march = next_scheduled_date(february, 1, 'month', anchor)
        self.assertEqual(february, date(2025, 2, 28))
        self.assertEqual(march, date(2025, 3, 31))

    def test_yearly_leap_day_returns_to_february_29(self):
        anchor = date(2024, 2, 29)
        due = anchor
        for _ in range(4):
            due = next_scheduled_date(due, 1, 'year', anchor)
        self.assertEqual(due, date(2028, 2, 29))

    def test_overdue_schedule_advances_to_first_future_date(self):
        next_due = next_future_due(
            date(2026, 1, 1), 1, 'month', date(2026, 1, 1),
            today=date(2026, 8, 14),
        )
        self.assertEqual(next_due, date(2026, 9, 1))

    def test_one_off_has_no_next_due_date(self):
        self.assertIsNone(
            next_future_due(
                date(2026, 8, 1), 1, 'once', date(2026, 8, 1),
                today=date(2026, 8, 14),
            )
        )


class TestMaintenanceRoutes(TestCase):
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
        self.user_id = user.id
        with self.client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_overdue_task_appears_on_homepage_and_can_be_completed(self):
        original_due = date.today() - timedelta(days=100)
        task = MaintenanceTask(
            name='Replace furnace filter', first_due_date=original_due,
            next_due_date=original_due, recurrence_interval=3,
            recurrence_unit='month', is_active=True,
        )
        db.session.add(task)
        db.session.commit()

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Replace furnace filter', response.data)
        self.assertIn(b'Overdue', response.data)

        response = self.client.post(
            f'/maintenance/{task.id}/complete',
            data={
                'completed_date': (date.today() - timedelta(days=2)).isoformat(),
                'notes': 'Used the final spare filter.',
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        completion = MaintenanceCompletion.query.one()
        self.assertEqual(completion.scheduled_due_date, original_due)
        self.assertEqual(completion.completed_by_user_id, self.user_id)
        self.assertEqual(completion.notes, 'Used the final spare filter.')
        self.assertGreater(task.next_due_date, date.today())

    def test_one_off_completion_retains_task_and_history(self):
        task = MaintenanceTask(
            name='Repair loose railing', first_due_date=date.today(),
            next_due_date=date.today(), recurrence_interval=1,
            recurrence_unit='once', is_active=True,
        )
        db.session.add(task)
        db.session.commit()

        response = self.client.post(
            f'/maintenance/{task.id}/complete',
            data={'completed_date': date.today().isoformat(), 'notes': ''},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(task.next_due_date)
        self.assertEqual(MaintenanceTask.query.count(), 1)
        self.assertEqual(MaintenanceCompletion.query.count(), 1)

    def test_future_completion_date_is_rejected(self):
        task = MaintenanceTask(
            name='Test alarms', first_due_date=date.today(),
            next_due_date=date.today(), recurrence_interval=6,
            recurrence_unit='month', is_active=True,
        )
        db.session.add(task)
        db.session.commit()

        response = self.client.post(
            f'/maintenance/{task.id}/complete',
            data={
                'completed_date': (date.today() + timedelta(days=1)).isoformat(),
                'notes': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'cannot be in the future', response.data)
        self.assertEqual(MaintenanceCompletion.query.count(), 0)

    def test_task_can_be_created_and_seen_on_calendar(self):
        due_date = date.today() + timedelta(days=5)
        response = self.client.post(
            '/maintenance/new',
            data={
                'name': 'Clean dryer vent',
                'description': 'Vacuum the full vent line.',
                'first_due_date': due_date.isoformat(),
                'recurrence_interval': '6',
                'recurrence_unit': 'month',
                'is_active': 'y',
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Clean dryer vent', response.data)
        task = MaintenanceTask.query.one()
        self.assertEqual(task.next_due_date, due_date)
        self.assertEqual(task.recurrence_interval, 6)

        response = self.client.get(
            f'/maintenance/calendar?year={due_date.year}&month={due_date.month}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Clean dryer vent', response.data)
