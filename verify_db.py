import sqlite3
from home_page import create_app, db
from home_page.models import User, Post

print(f"SQLite version: {sqlite3.sqlite_version}")
print(f"SQLite library version: {sqlite3.version}")

app = create_app()

with app.app_context():
    try:
        print("Attempting to connect to the database...")
        user_count = User.query.count()
        print(f"User count: {user_count}")
        post_count = Post.query.count()
        print(f"Post count: {post_count}")
        
        print("Checking for orphaned posts...")
        posts = Post.query.all()
        orphaned_posts = []
        for post in posts:
            if not post.author:
                orphaned_posts.append(post)
                print(f"Orphaned post found: ID={post.id}, Title={post.title}")
        
        if orphaned_posts:
            print(f"Found {len(orphaned_posts)} orphaned posts.")
        else:
            print("No orphaned posts found.")

        # Create test user
        print("Creating test user...")
        from home_page import bcrypt
        hashed_password = bcrypt.generate_password_hash('password').decode('utf-8')
        user = User.query.filter_by(email='test@example.com').first()
        if not user:
            user = User(username='testuser', email='test@example.com', password=hashed_password)
            db.session.add(user)
            db.session.commit()
            print("Test user created.")
        else:
            print("Test user already exists.")

        print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")
