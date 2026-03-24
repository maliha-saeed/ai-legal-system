"""
Legal Intake & Document Automation System
Flask Application Entry Point

This file is the starting point of the entire application.
Running this file directly starts the web server.
"""

# Flask is the web framework that handles HTTP requests and responses
from flask import Flask

# init_db() sets up the SQLite database tables on first run
from database import init_db

# register_routes() connects all URL endpoints (e.g. /intake, /case/1) to the app
from routes import register_routes

# os is a built-in Python module used for file paths and folder creation
import os


def create_app():
    """
    Application factory function.

    Instead of creating the Flask app at module level (a common beginner pattern),
    we wrap it in a function. This makes it easier to:
      - Create multiple app instances (e.g. one for testing, one for production)
      - Configure the app differently per environment
    """

    # Create the Flask application instance.
    # __name__ tells Flask where to look for templates and static files
    # (i.e. in the same directory as this file).
    app = Flask(__name__)

    # Secret key is used by Flask to cryptographically sign session cookies
    # and flash messages. os.urandom(24) generates a random 24-byte key
    # each time the app starts — fine for development.
    # In production, this should be a fixed key stored in an environment variable
    # so sessions survive server restarts.
    app.secret_key = os.urandom(24)

    # Tell Flask where to save uploaded files.
    # os.path.dirname(__file__) gets the directory this file lives in,
    # then we append 'uploads' to build an absolute path like:
    # /home/user/legal_intake/uploads
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

    # Limit uploaded file size to 5MB.
    # 5 * 1024 * 1024 = 5,242,880 bytes = 5MB.
    # Flask will automatically reject any upload larger than this with a 413 error.
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

    # Create the uploads folder if it doesn't already exist.
    # exist_ok=True means no error is raised if the folder is already there.
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialise the database — creates the SQLite file and all tables
    # (cases, documents, templates) if they don't already exist.
    # Safe to call on every startup; it won't overwrite existing data.
    init_db()

    # Register all URL routes defined in routes.py onto this app instance.
    # Without this step, visiting any URL would return a 404.
    register_routes(app)

    # Return the fully configured app to the caller
    return app


# This block only runs when you execute this file directly:
#   python app.py
# It does NOT run when the file is imported by another module (e.g. during testing),
# which is the main reason for the `if __name__ == '__main__'` guard.
if __name__ == '__main__':

    # Build the app using the factory function above
    app = create_app()

    # Start the Flask development server
    # port=5000 means the app is accessible at http://localhost:5000
    app.run(debug=True, port=5000)