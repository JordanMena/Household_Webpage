from datetime import date, timedelta
from unittest import TestCase

from home_page import bcrypt, create_app, db
from home_page.maintenance.scheduling import next_due_date
from home_page.models import MaintenanceCompletion, MaintenanceTask, User


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


class TestMaintenanceScheduling(TestCase):
    def test_next_due_is_one_interval_after_completion(self):
        cases = [
            (date(2026, 10, 10), 5, 'day', date(2026, 10, 15)),
            (date(2026, 10, 10), 2, 'week', date(2026, 10, 24)),
            (date(2026, 11, 15), 3, 'month', date(2027, 2, 15)),
            (date(2026, 10, 10), 2, 'year', date(2028, 10, 10)),
        ]
        for completed, interval, unit, expected in cases:
            with self.subTest(unit=unit):
                self.assertEqual(next_due_date(completed, interval, unit), expected)

    def test_month_end_uses_completion_day_and_clamps_short_months(self):
        self.assertEqual(
            next_due_date(date(2025, 1, 31), 1, 'month'), date(2025, 2, 28)
        )
        self.assertEqual(
            next_due_date(date(2025, 2, 28), 1, 'month'), date(2025, 3, 28)
        )

    def test_yearly_leap_day_clamps_to_end_of_february(self):
        self.assertEqual(
            next_due_date(date(2024, 2, 29), 1, 'year'), date(2025, 2, 28)
        )
        self.assertEqual(
            next_due_date(date(2024, 2, 29), 4, 'year'), date(2028, 2, 29)
        )

    def test_one_off_has_no_next_due_date(self):
        self.assertIsNone(
            next_due_date(date(2026, 8, 1), 1, 'once')
        )

    def test_invalid_recurrence_is_rejected(self):
        with self.assertRaises(ValueError):
            next_due_date(date(2026, 10, 10), 0, 'day')
        with self.assertRaises(ValueError):
            next_due_date(date(2026, 10, 10), 1, 'invalid')


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
        self.assertEqual(
            task.next_due_date,
            next_due_date(date.today() - timedelta(days=2), 3, 'month'),
        )

    def test_daily_completion_uses_entered_date_for_early_and_late_tasks(self):
        today = date.today()
        cases = [
            ('Late completion', today - timedelta(days=60), today),
            ('Early completion', today + timedelta(days=30), today),
            ('Backdated completion', today - timedelta(days=60),
             today - timedelta(days=10)),
            ('Due today after completion', today - timedelta(days=60),
             today - timedelta(days=5)),
        ]
        for name, original_due, completed in cases:
            with self.subTest(name=name):
                task = MaintenanceTask(
                    name=name, first_due_date=original_due,
                    next_due_date=original_due, recurrence_interval=5,
                    recurrence_unit='day', is_active=True,
                )
                db.session.add(task)
                db.session.commit()
                response = self.client.post(
                    f'/maintenance/{task.id}/complete',
                    data={'completed_date': completed.isoformat(), 'notes': ''},
                    follow_redirects=True,
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(task.next_due_date, completed + timedelta(days=5))
                completion = MaintenanceCompletion.query.filter_by(task_id=task.id).one()
                self.assertEqual(completion.scheduled_due_date, original_due)
                self.assertEqual(completion.completed_date, completed)
                if task.next_due_date < today:
                    self.assertIn(b'Overdue', response.data)

    def test_repeated_completion_on_same_day_does_not_push_due_date_forward(self):
        today = date.today()
        task = MaintenanceTask(
            name='Repeat completion', first_due_date=today - timedelta(days=60),
            next_due_date=today - timedelta(days=60), recurrence_interval=5,
            recurrence_unit='day', is_active=True,
        )
        db.session.add(task)
        db.session.commit()
        for _ in range(2):
            response = self.client.post(
                f'/maintenance/{task.id}/complete',
                data={'completed_date': today.isoformat(), 'notes': ''},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(task.next_due_date, today + timedelta(days=5))
        self.assertEqual(MaintenanceCompletion.query.filter_by(task_id=task.id).count(), 2)

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
