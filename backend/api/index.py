"""Vercel serverless entrypoint — exposes the Django WSGI app."""

import os
import sys

# Make the backend root importable when Vercel runs this file from api/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.wsgi import application  # noqa: E402

app = application
