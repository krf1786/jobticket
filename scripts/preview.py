#!/usr/bin/env python3
"""Loopback-only, non-persistent preview of the captured Job Ticket frontend.

No production service is contacted. All API requests and writes are rejected.
DEMO01 is synthetic; teams=1 exposes the existing Teams UI for mocked tests.
"""
import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "frontend/ticket.html"
PREFIX = "/jobticket"


def bootstrap(saved=False, teams=False):
    name = "Demonstration ticket" if saved else ""
    return {
        "jobId": "DEMO01" if saved else None,
        "jobName": name,
        "prefix": PREFIX,
        "saving": saved,
        "state": {
            "jobName": name, "date": "", "qty": "", "due": "", "time": "",
            "materials": [""], "steps": [{"op": "", "instr": ""}],
            "notes": "", "image": None,
        },
        "sync": {"ready": bool(saved and teams)},
    }


def render(boot):
    # Escape before embedding JSON in a script element, including closing tags.
    payload = json.dumps(boot).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    title = html.escape(boot.get("jobName") or "Job Ticket")
    values = {"__TITLE__": title, "__BOOTSTRAP__": payload}
    return re.sub(r"__TITLE__|__BOOTSTRAP__", lambda match: values[match[0]], TEMPLATE.read_text(encoding="utf-8"))


class PreviewHandler(BaseHTTPRequestHandler):
    def respond(self, code, body, content_type):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Preview-Only", "no-storage-no-upstream")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def reject_api(self):
        self.respond(405, json.dumps({"ok": False, "error": "Local preview only: saving, uploads and Teams pushes are disabled"}), "application/json")

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path in ("/", PREFIX, PREFIX + "/"):
            return self.respond(200, render(bootstrap()), "text/html; charset=utf-8")
        if url.path == PREFIX + "/DEMO01":
            teams = parse_qs(url.query).get("teams") == ["1"]
            return self.respond(200, render(bootstrap(saved=True, teams=teams)), "text/html; charset=utf-8")
        if url.path.startswith(PREFIX + "/api/"):
            return self.reject_api()
        # Explicit allowlist; never serve raw captures, .git, or arbitrary files.
        assets = {PREFIX + "/static/fonts.css": ROOT / "frontend/static/fonts.css"}
        for weight in (400, 600, 700):
            filename = f"inter-latin-{weight}-normal.woff2"
            assets[PREFIX + "/static/fonts/" + filename] = ROOT / "frontend/static/fonts" / filename
        if url.path in assets:
            path = assets[url.path]
            return self.respond(200, path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.respond(404, "Local preview route not found", "text/plain")

    do_PUT = reject_api
    do_POST = reject_api
    do_PATCH = reject_api
    do_DELETE = reject_api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), PreviewHandler)
    print(f"Preview: http://127.0.0.1:{args.port}/jobticket/", flush=True)
    print(f"Synthetic saved view: http://127.0.0.1:{args.port}/jobticket/DEMO01", flush=True)
    print("Local preview only: all API calls are rejected; nothing is persisted or sent upstream.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
