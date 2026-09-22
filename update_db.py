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
        columns = {column['name'] for column in inspect(connection).get_columns('recipe')}
        for name, sql_type in (
            ('servings', 'VARCHAR(80)'), ('prep_time_minutes', 'INTEGER'),
            ('cook_time_minutes', 'INTEGER'), ('ingredient_groups', 'JSON'),
            ('direction_steps', 'JSON'),
        ):
            if name not in columns:
                connection.execute(text(f'ALTER TABLE recipe ADD COLUMN {name} {sql_type}'))
        # SQLite does not enforce VARCHAR lengths. Other supported deployments
        # need their column widths updated explicitly.
        if connection.dialect.name == 'postgresql':
            connection.execute(text('ALTER TABLE recipe ALTER COLUMN name TYPE VARCHAR(160)'))
            connection.execute(text('ALTER TABLE recipe ALTER COLUMN source TYPE VARCHAR(160)'))
        elif connection.dialect.name in ('mysql', 'mariadb'):
            connection.execute(text('ALTER TABLE recipe MODIFY name VARCHAR(160) NOT NULL'))
            connection.execute(text('ALTER TABLE recipe MODIFY source VARCHAR(160) NULL'))
    print("Database schema is up to date.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        update_db()
