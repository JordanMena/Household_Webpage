"""WSGI entry point used by the production web server."""

from home_page import create_app


app = create_app()
