import os
import sys

# Add web/ directory to Python path so relative imports inside web/ work seamlessly
web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
if web_dir not in sys.path:
    sys.path.insert(0, web_dir)

from web.app import _ensure_schema, app, db  # noqa: E402

# Automatically ensure Azure SQL tables exist on first startup
with app.app_context():
    try:
        db.create_all()
        _ensure_schema(app)
        app.logger.info("Database tables verified/created successfully.")
    except Exception as e:
        app.logger.warning("Could not auto-create tables on startup: %s", e)

if __name__ == "__main__":
    app.run()
