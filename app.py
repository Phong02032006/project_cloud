import os
import sys

# Add web/ directory to Python path so relative imports inside web/ work seamlessly
web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
if web_dir not in sys.path:
    sys.path.insert(0, web_dir)

from sqlalchemy import inspect, text  # noqa: E402
from web.app import app, db  # noqa: E402

# Automatically ensure Azure SQL tables and new columns exist on startup
with app.app_context():
    try:
        db.create_all()
        cols = {c["name"] for c in inspect(db.engine).get_columns("users")}
        if "password_hash" not in cols:
            db.session.execute(text("ALTER TABLE users ADD password_hash VARCHAR(255)"))
            db.session.commit()
            app.logger.info("Added password_hash column to users table.")
        app.logger.info("Database tables verified/created successfully.")
    except Exception as e:
        app.logger.warning("Could not auto-create/migrate tables on startup: %s", e)

if __name__ == "__main__":
    app.run()
