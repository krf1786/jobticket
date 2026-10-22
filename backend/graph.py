"""
Microsoft Graph push: render a ticket to PDF and drop it in the job's channel folder.

Entirely optional. With no credentials in graph.env the module reports disabled
and the rest of the app carries on exactly as before.
"""
import json, os, pathlib, threading, time, urllib.parse, urllib.request, urllib.error
from typing import Optional, Tuple

BASE     = pathlib.Path(__file__).resolve().parent
ENV_FILE = BASE / "graph.env"
GRAPH    = "https://graph.microsoft.com/v1.0"

_token: dict = {"value": None, "expires": 0.0}
_token_lock = threading.Lock()
_site_cache: dict = {}


# ------------------------------------------------------------------ config
def cfg() -> dict:
    """Read graph.env on every call so credentials can be added without a restart."""
    out = {}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        if k.startswith(("GRAPH_", "PUSH_")):
            out[k] = v
    return out


def enabled() -> bool:
    c = cfg()
    return all(c.get(k) for k in
               ("GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET",
                "GRAPH_SITE_HOSTNAME", "GRAPH_SITE_PATH"))


def status() -> dict:
    c = cfg()
    missing = [k for k in ("GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET",
                           "GRAPH_SITE_HOSTNAME", "GRAPH_SITE_PATH") if not c.get(k)]
    return {"enabled": not missing, "missing": missing,
            "site": (c.get("GRAPH_SITE_HOSTNAME", "") + c.get("GRAPH_SITE_PATH", "")) or None}


# ------------------------------------------------------------------- http
def _req(url: str, method="GET", data=None, headers=None, timeout=60) -> bytes:
    r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return resp.read()


def token() -> str:
    with _token_lock:
        if _token["value"] and time.time() < _token["expires"] - 120:
            return _token["value"]
        c = cfg()
        body = urllib.parse.urlencode({
            "client_id": c["GRAPH_CLIENT_ID"],
            "client_secret": c["GRAPH_CLIENT_SECRET"],
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }).encode()
        url = f"https://login.microsoftonline.com/{c['GRAPH_TENANT_ID']}/oauth2/v2.0/token"
        j = json.loads(_req(url, "POST", body,
                            {"Content-Type": "application/x-www-form-urlencoded"}))
        _token["value"] = j["access_token"]
        _token["expires"] = time.time() + int(j.get("expires_in", 3600))
        return _token["value"]


def _auth() -> dict:
    return {"Authorization": "Bearer " + token()}


def site_and_drive() -> Tuple[str, str]:
    """Resolve the SharePoint site and its default document library. Cached."""
    c = cfg()
    key = c["GRAPH_SITE_HOSTNAME"] + c["GRAPH_SITE_PATH"]
    if key in _site_cache:
        return _site_cache[key]
    host = c["GRAPH_SITE_HOSTNAME"].strip("/")
    path = "/" + c["GRAPH_SITE_PATH"].strip("/")
    site = json.loads(_req(f"{GRAPH}/sites/{host}:{path}", headers=_auth()))
    site_id = site["id"]

    want = (c.get("GRAPH_DRIVE_NAME") or "").strip().lower()
    drives = json.loads(_req(f"{GRAPH}/sites/{site_id}/drives", headers=_auth()))["value"]
    drive_id = None
    if want:
        for d in drives:
            if d.get("name", "").lower() == want:
                drive_id = d["id"]
                break
    if not drive_id:
        drive_id = json.loads(_req(f"{GRAPH}/sites/{site_id}/drive", headers=_auth()))["id"]

    _site_cache[key] = (site_id, drive_id)
    return site_id, drive_id


def _seg(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def upload(folder_name: str, file_name: str, blob: bytes) -> dict:
    """PUT the file into <library>/<folder_name>/<file_name>, creating the folder if needed."""
    _, drive_id = site_and_drive()
    path = f"{_seg(folder_name)}/{_seg(file_name)}"
    url = f"{GRAPH}/drives/{drive_id}/root:/{path}:/content"
    try:
        j = json.loads(_req(url, "PUT", blob,
                            {**_auth(), "Content-Type": "application/pdf"}, timeout=120))
    except urllib.error.HTTPError as e:
        if e.code == 404:                       # folder missing -> create, retry once
            body = json.dumps({"name": folder_name, "folder": {},
                               "@microsoft.graph.conflictBehavior": "fail"}).encode()
            try:
                _req(f"{GRAPH}/drives/{drive_id}/root/children", "POST", body,
                     {**_auth(), "Content-Type": "application/json"})
            except urllib.error.HTTPError:
                pass
            j = json.loads(_req(url, "PUT", blob,
                                {**_auth(), "Content-Type": "application/pdf"}, timeout=120))
        else:
            raise
    return {"name": j.get("name"), "webUrl": j.get("webUrl"), "size": j.get("size")}
