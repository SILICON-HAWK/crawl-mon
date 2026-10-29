"""Controlled loopback site used by collection integration tests."""

from collections import Counter
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import time


@contextmanager
def fixture_site():
    hits = Counter()
    jobs = (Path(__file__).parent / "fixtures" / "jobs.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits[self.path] += 1
            status = 200
            if self.path == "/robots.txt":
                body = b"User-agent: *\nAllow: /\n"
            elif self.path == "/":
                body = b'<html><a href="/jobs">Jobs</a><a href="/jobs#duplicate">Again</a></html>'
            elif self.path == "/mixed":
                body = b'<html><a href="/jobs">Jobs</a><a href="/failure">Failure</a></html>'
            elif self.path == "/jobs":
                body = jobs
            elif self.path == "/slow":
                time.sleep(3)
                body = jobs
            else:
                status, body = 503, b"<html>Temporarily unavailable</html>"
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", hits
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
