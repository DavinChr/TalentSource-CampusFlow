import os
import sys

# Add the project root directory to the Python path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from a2wsgi import ASGIMiddleware
from src.web import app

# WSGI application callable for PythonAnywhere, Gunicorn, Apache mod_wsgi, etc.
application = ASGIMiddleware(app)
