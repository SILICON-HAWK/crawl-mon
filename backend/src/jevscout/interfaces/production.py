"""Serve a built frontend with the local API from a fixed snapshot directory."""
import os
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from jevscout.interfaces.api import app

frontend_dir = Path(os.environ.get('JEVSCOUT_FRONTEND_DIR', 'frontend/dist-stable'))

@app.get('/jobs', include_in_schema=False)
@app.get('/runs', include_in_schema=False)
@app.get('/profile', include_in_schema=False)
def frontend_page():
    return FileResponse(frontend_dir / 'index.html')

app.mount('/', StaticFiles(directory=frontend_dir, html=True), name='frontend')
