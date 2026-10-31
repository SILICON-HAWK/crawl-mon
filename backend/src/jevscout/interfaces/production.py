"""Serve a built frontend with the local API from a fixed snapshot directory."""
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from jevscout.interfaces.api import app

frontend_dir = Path(os.environ.get('JEVSCOUT_FRONTEND_DIR', 'frontend/dist-stable'))
app.mount('/', StaticFiles(directory=frontend_dir, html=True), name='frontend')
