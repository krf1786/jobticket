#!/usr/bin/env python3
"""
Job Ticket service  ·  graphlab.info/jobticket
Single-file FastAPI app. SQLite storage, one row per job.

  GET  /jobticket/                 blank scratch ticket (nothing saved)
  GET  /jobticket/{job}            that job's ticket (creates on first visit)
  GET  /jobticket/api/{job}        current state as JSON
  PUT  /jobticket/api/{job}        save state
  POST /jobticket/api/{job}/image  upload reference image
  GET  /jobticket/uploads/{f}      serve uploaded image
  GET  /jobticket/health           liveness probe
"""
import json, math, os, re, sqlite3, time, uuid, pathlib, threading
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import graph, pdf

BASE     = pathlib.Path(__file__).resolve().parent
DB_PATH  = BASE / "tickets.db"
UPLOADS  = BASE / "uploads"
STATIC   = BASE / "static"
TEMPLATE = BASE / "ticket.html"
PREFIX   = "/jobticket"
MAX_IMAGE_BYTES = 12 * 1024 * 1024
PORT = int(os.environ.get("PORT", 10290))

UPLOADS.mkdir(exist_ok=True)
STATIC.mkdir(exist_ok=True)

app = FastAPI(title="Job Ticket", docs_url=None, redoc_url=None)
_lock = threading.Lock()
_push_lock = threading.Lock()     # serialize render + upload in this single-worker service


# ---------------------------------------------------------------- database
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                job_id     TEXT PRIMARY KEY,
                job_name   TEXT NOT NULL DEFAULT '',
                data       TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(tickets)")}
        if "pushed_at" not in cols:
            conn.execute("ALTER TABLE tickets ADD COLUMN pushed_at REAL NOT NULL DEFAULT 0")
        if "push_error" not in cols:
            conn.execute("ALTER TABLE tickets ADD COLUMN push_error TEXT NOT NULL DEFAULT ''")


init_db()


# ------------------------------------------------------- Teams PDF snapshot
def snapshot_filename(job_name: str, job_id: str) -> str:
    base = (job_name or job_id).strip()
    if base.upper().startswith("SB"):
        base = base[2:]                      # "SB0820 - Elegant Plaque" -> "0820 - Elegant Plaque"
    base = re.sub(r'[\\/:*?"<>|]', "-", base).strip() or job_id
    return base + ".pdf"


def push_ticket(job_id: str) -> dict:
    """Render this ticket to PDF and drop it in the job's channel folder."""
    # The PDF module serializes rendering only. Keep uploads in the same order
    # too, so an older in-flight upload cannot overwrite a newer PDF.
    with _push_lock:
        return _push_ticket(job_id)


def _push_ticket(job_id: str) -> dict:
    row = get_ticket(job_id)
    if row is None:
        return {"ok": False, "error": "no such job"}
    if not graph.enabled():
        return {"ok": False, "error": "graph credentials not configured"}
    if not pdf.available():
        return {"ok": False, "error": "pdf renderer not installed"}

    folder = (row["job_name"] or job_id).strip()
    fname = snapshot_filename(row["job_name"], job_id)
    rendered_revision = row["updated_at"]
    try:
        blob = pdf.render(f"http://127.0.0.1:{PORT}{PREFIX}/{job_id}")
        info = graph.upload(folder, fname, blob)
        with _lock, db() as conn:
            conn.execute("UPDATE tickets SET pushed_at=?, push_error='' WHERE job_id=?",
                         (rendered_revision, job_id))
        # Rendering may have seen an even newer save. Acknowledge only the
        # revision known before rendering; any later save remains queued.
        return {"ok": True, "pushedAt": rendered_revision, "file": info}
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"[:400]
        with _lock, db() as conn:
            conn.execute("UPDATE tickets SET push_error=? WHERE job_id=?", (msg, job_id))
        return {"ok": False, "error": msg}


def sync_worker() -> None:
    """Push tickets that have gone quiet, so the folder copy trails edits by ~a minute."""
    while True:
        try:
            time.sleep(20)
            if not (graph.enabled() and pdf.available()):
                continue
            idle = float(graph.cfg().get("PUSH_IDLE_SECONDS", 60))
            cutoff = time.time() - idle
            with db() as conn:
                rows = conn.execute(
                    "SELECT job_id FROM tickets WHERE updated_at > pushed_at"
                    " AND updated_at < ? LIMIT 5", (cutoff,)).fetchall()
            for r in rows:
                push_ticket(r["job_id"])
        except Exception:
            pass


threading.Thread(target=sync_worker, daemon=True).start()


# ---------------------------------------------------------------- helpers
JOB_RE = re.compile(r"[^A-Za-z0-9_-]+")


def normalize_job_id(raw: str) -> str:
    """'SB0820 - Elegant Plaque' or 'sb0820' -> 'SB0820'. Anything else -> a safe slug."""
    raw = (raw or "").strip()
    m = re.match(r"^\s*([A-Za-z]{1,4}\d{2,6})\b", raw)
    if m:
        return m.group(1).upper()
    slug = JOB_RE.sub("-", raw).strip("-")[:64].upper()
    return slug


def default_state(job_name: str) -> dict:
    return {
        "jobName": job_name, "date": "", "qty": "", "due": "", "time": "",
        "materials": [""], "steps": [{"op": "", "instr": ""}],
        "notes": "", "image": None,
    }


def get_ticket(job_id: str) -> Optional[sqlite3.Row]:
    with db() as conn:
        return conn.execute("SELECT * FROM tickets WHERE job_id = ?", (job_id,)).fetchone()


def preserve_material_details(state: dict, previous: dict) -> None:
    """An omitted field is an old client, not an instruction to erase details."""
    if "materialDetails" in state or "materialDetails" not in previous:
        return
    details = previous["materialDetails"]
    if state.get("materials") == previous.get("materials"):
        state["materialDetails"] = details
        return
    if isinstance(details, list) and any(isinstance(value, str) and value for value in details):
        # Index-based details cannot safely be mapped after an old tab renames,
        # reorders or removes rows (especially duplicate material names).
        raise HTTPException(409, "This ticket has material details. Reload the updated editor before changing material rows.")
    materials = state.get("materials")
    state["materialDetails"] = [""] * len(materials) if isinstance(materials, list) else []


def create_ticket(job_id: str, job_name: str) -> sqlite3.Row:
    now = time.time()
    with _lock, db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO tickets (job_id, job_name, data, created_at, updated_at)"
            " VALUES (?,?,?,?,?)",
            (job_id, job_name, json.dumps(default_state(job_name)), now, now),
        )
    return get_ticket(job_id)


def render(state: dict, job_id: Optional[str], job_name: str) -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    sync = {"ready": graph.enabled() and pdf.available()}
    boot = {"jobId": job_id, "jobName": job_name, "prefix": PREFIX,
            "saving": job_id is not None, "state": state, "sync": sync}
    payload = json.dumps(boot).replace("</", "<\\/")
    title = (job_name or "Job Ticket").replace("<", "&lt;").replace(">", "&gt;")
    return html.replace("__BOOTSTRAP__", payload).replace("__TITLE__", title)


# ---------------------------------------------------------------- routes
@app.get(f"{PREFIX}/health")
def health():
    with db() as conn:
        n = conn.execute("SELECT COUNT(*) c FROM tickets").fetchone()["c"]
    return {"ok": True, "tickets": n,
            "graph": graph.status()["enabled"], "renderer": pdf.available()}


@app.get(f"{PREFIX}/uploads/{{filename}}")
def serve_upload(filename: str):
    safe = os.path.basename(filename)
    path = UPLOADS / safe
    if not path.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get(f"{PREFIX}/api/{{job}}")
def api_get(job: str):
    job_id = normalize_job_id(job)
    row = get_ticket(job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    return {"jobId": row["job_id"], "jobName": row["job_name"],
            "state": json.loads(row["data"]), "updatedAt": row["updated_at"]}


@app.put(f"{PREFIX}/api/{{job}}")
async def api_put(job: str, request: Request):
    job_id = normalize_job_id(job)
    if not job_id:
        raise HTTPException(400, "bad job id")
    try:
        state: Any = await request.json()
    except Exception:
        raise HTTPException(400, "body must be JSON")
    if not isinstance(state, dict):
        raise HTTPException(400, "body must be a JSON object")

    job_name = str(state.get("jobName") or "")
    with _lock, db() as conn:
        previous = conn.execute("SELECT data, updated_at FROM tickets WHERE job_id = ?", (job_id,)).fetchone()
        now = time.time()
        if previous:
            preserve_material_details(state, json.loads(previous["data"]))
            # updated_at doubles as the saved revision. Keep it strictly
            # increasing even for same-tick saves or a backwards clock step.
            now = max(now, math.nextafter(previous["updated_at"], math.inf))
            conn.execute("UPDATE tickets SET job_name=?, data=?, updated_at=? WHERE job_id=?",
                         (job_name, json.dumps(state), now, job_id))
        else:
            conn.execute("INSERT INTO tickets (job_id, job_name, data, created_at, updated_at)"
                         " VALUES (?,?,?,?,?)", (job_id, job_name, json.dumps(state), now, now))
    return {"ok": True, "savedAt": now}


@app.post(f"{PREFIX}/api/{{job}}/image")
async def api_image(job: str, file: UploadFile = File(...)):
    job_id = normalize_job_id(job)
    if not job_id:
        raise HTTPException(400, "bad job id")
    blob = await file.read()
    if len(blob) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "image too large (12 MB max)")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(415, "not an image")
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
           "image/webp": ".webp"}.get(file.content_type, ".bin")
    name = f"{job_id}-{uuid.uuid4().hex[:10]}{ext}"
    (UPLOADS / name).write_bytes(blob)
    return {"ok": True, "url": f"{PREFIX}/uploads/{name}"}


@app.get(f"{PREFIX}/api/{{job}}/sync")
def api_sync_status(job: str):
    job_id = normalize_job_id(job)
    row = get_ticket(job_id)
    st = graph.status()
    st["renderer"] = pdf.available()
    st["ready"] = bool(st["enabled"] and st["renderer"])
    if row is not None:
        st["pushedAt"] = row["pushed_at"]
        st["error"] = row["push_error"]
        st["stale"] = row["updated_at"] > row["pushed_at"]
    return st


@app.post(f"{PREFIX}/api/{{job}}/push")
def api_push(job: str):
    job_id = normalize_job_id(job)
    res = push_ticket(job_id)
    return JSONResponse(res, status_code=200 if res.get("ok") else 409)


@app.get(PREFIX, include_in_schema=False)
def blank_redirect():
    return RedirectResponse(f"{PREFIX}/")


@app.get(f"{PREFIX}/", response_class=HTMLResponse)
def blank_ticket():
    """Unchanged behaviour from the old static page: a scratch ticket, nothing saved."""
    return HTMLResponse(render(default_state(""), None, ""))


@app.get(PREFIX + "/{job}", response_class=HTMLResponse)
def job_ticket(job: str, name: str = ""):
    job_id = normalize_job_id(job)
    if not job_id:
        raise HTTPException(404, "not found")
    row = get_ticket(job_id)
    if row is None:
        display = name.strip() or job.strip()
        row = create_ticket(job_id, display)
    elif name.strip() and not row["job_name"]:
        with _lock, db() as conn:
            conn.execute("UPDATE tickets SET job_name=? WHERE job_id=?", (name.strip(), job_id))
        row = get_ticket(job_id)
    state = json.loads(row["data"])
    state.setdefault("jobName", row["job_name"])
    return HTMLResponse(render(state, row["job_id"], row["job_name"]))


app.mount(f"{PREFIX}/static", StaticFiles(directory=STATIC), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", 10290)))
