"""Apply additive schema updates to the configured application database."""
from sqlalchemy import inspect, text
from home_page import create_app, db


def update_db():
    db.create_all()
    with db.engine.begin() as connection:
        columns = {column['name'] for column in inspect(connection).get_columns('tag')}
        if 'color' not in columns:
            connection.execute(text("ALTER TABLE tag ADD COLUMN color TEXT NOT NULL DEFAULT 'primary'"))
            connection.execute(text("UPDATE tag SET color = 'danger' WHERE name = 'meat'"))
            connection.execute(text("UPDATE tag SET color = 'success' WHERE name = 'vegetarian'"))
        columns = {column['name'] for column in inspect(connection).get_columns('freezer_item')}
        if 'category' not in columns:
            connection.execute(text("ALTER TABLE freezer_item ADD COLUMN category VARCHAR(30) NOT NULL DEFAULT 'Misc'"))
    print("Database schema is up to date.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        update_db()
