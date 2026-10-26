"""Shared corkboard layout. Ticket content stays in the existing ticket service."""
import json
import math
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, unquote

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

SITE = "https://jplak-ticket-corkboard.krf1786.chatgpt.site"
FIELDS = {"href", "label", "x", "y", "color", "sample", "z"}


def clean_pin(pin):
    if not isinstance(pin, dict):
        raise ValueError("Invalid ticket")
    key = pin.get("id", "")
    if not isinstance(key, str) or not re.fullmatch(r"[A-Z0-9_-]{1,64}", key) or key.lower() in {"api", "health", "uploads", "static"}:
        raise ValueError("Invalid job number")
    href = pin.get("href") or "https://graphlab.info/jobticket/" + key
    url = urlsplit(href)
    if (len(href) > 4096 or url.scheme != "https" or url.netloc != "graphlab.info"
            or unquote(url.path).rstrip("/").upper() != "/JOBTICKET/" + key):
        raise ValueError("Invalid ticket link")
    result = {"id": key, "href": href, "label": str(pin.get("label", ""))[:120],
              "color": pin.get("color", "#6c8879"), "sample": pin.get("sample") is True}
    if result["color"] not in ["#6c8879", "#be6954", "#c6a35d", "#6d8dba"]:
        result["color"] = "#6c8879"
    for field in ["x", "y", "z"]:
        value = pin.get(field, 0)
        if not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("Invalid position")
        result[field] = max(0, min(1000000 if field == "z" else 20000, value))
    return result


def create_router(database):
    database = Path(database)
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS board (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, initialized INTEGER NOT NULL, pins TEXT NOT NULL)")
        conn.execute("INSERT OR IGNORE INTO board VALUES (1,0,0,'[]')")
        conn.execute("CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY)")
    router = APIRouter()

    def read(conn):
        row = conn.execute("SELECT revision,initialized,pins FROM board WHERE id=1").fetchone()
        return {"revision": row[0], "initialized": bool(row[1]), "pins": json.loads(row[2])}

    @router.api_route("/jobticket/corkboard/api", methods=["GET", "POST", "OPTIONS"])
    async def layout(request: Request):
        origin = request.headers.get("origin", "")
        allowed = origin in [SITE, "https://graphlab.info", "null"] or bool(re.fullmatch(r"http://(?:localhost|127\.0\.0\.1)(?::\d+)?", origin))
        headers = {"Cache-Control": "no-store", "Vary": "Origin"}
        if allowed:
            headers.update({"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"})
        if request.method == "OPTIONS":
            return Response(status_code=204 if allowed else 403, headers=headers)
        if request.method == "POST" and not allowed:
            return JSONResponse({"error": "Origin not allowed"}, status_code=403, headers=headers)
        try:
            with sqlite3.connect(database, timeout=10) as conn:
                if request.method == "GET":
                    return JSONResponse(read(conn), headers=headers)
                if request.headers.get("content-type", "").split(";")[0] != "application/json":
                    raise ValueError("JSON required")
                raw = bytearray()
                async for chunk in request.stream():
                    raw.extend(chunk)
                    if len(raw) > 600000:
                        raise ValueError("Layout too large")
                data = json.loads(raw)
                operation_id = data.get("operationId", "")
                if not re.fullmatch(r"[a-zA-Z0-9_-]{8,100}", operation_id):
                    raise ValueError("Invalid operation ID")
                conn.execute("BEGIN IMMEDIATE")
                state = read(conn)
                if conn.execute("SELECT 1 FROM receipts WHERE id=?", (operation_id,)).fetchone():
                    return JSONResponse(state, headers=headers)
                pins = {pin["id"]: pin for pin in state["pins"]}
                if data.get("initialize"):
                    if not state["initialized"]:
                        incoming = data.get("pins", [])
                        if not isinstance(incoming, list) or len(incoming) > 100:
                            raise ValueError("Too many tickets")
                        pins = {pin["id"]: pin for pin in map(clean_pin, incoming)}
                else:
                    operations = data.get("operations")
                    if not isinstance(operations, list) or len(operations) > 300:
                        raise ValueError("Invalid operations")
                    for op in operations:
                        kind, key = op.get("type"), op.get("id")
                        if kind == "remove":
                            pins.pop(key, None)
                        elif kind == "add":
                            pin = clean_pin(op.get("pin"))
                            pins.setdefault(pin["id"], pin)
                        elif kind == "patch":
                            if key in pins:
                                changes = op.get("changes", {})
                                if not isinstance(changes, dict) or not set(changes) <= FIELDS:
                                    raise ValueError("Invalid changes")
                                pins[key] = clean_pin({**pins[key], **changes})
                        else:
                            raise ValueError("Invalid operation")
                if len(pins) > 100:
                    raise ValueError("Keep this board to 100 tickets or fewer")
                conn.execute("UPDATE board SET revision=revision+1,initialized=1,pins=? WHERE id=1", (json.dumps(list(pins.values())),))
                conn.execute("INSERT INTO receipts VALUES (?)", (operation_id,))
                return JSONResponse(read(conn), headers=headers)
        except (ValueError, TypeError, AttributeError) as error:
            return JSONResponse({"error": str(error)}, status_code=400, headers=headers)

    return router
