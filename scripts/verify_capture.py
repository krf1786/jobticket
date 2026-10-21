#!/usr/bin/env python3
"""Offline checks for capture integrity, syntax, template reuse and preview safety."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from capture_frontend import capture, normalize
from preview import ROOT, TEMPLATE, PreviewHandler, ThreadingHTTPServer, bootstrap, render


def main():
    manifest = json.loads((ROOT / "docs/source-manifest.json").read_text())
    for relative, expected in manifest["files"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    source = TEMPLATE.read_text()
    assert source.count("__TITLE__") == source.count("__BOOTSTRAP__") == 1
    assert "window.__TICKET__ = __BOOTSTRAP__;" in source
    assert "graphlab.info" not in source
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        for mode in (False, True):
            result = render(bootstrap(saved=mode))
            assert normalize(result) == source
            (directory / str(mode)).write_text(result)
        assert capture(directory / "False", directory / "True") == TEMPLATE.read_bytes()
        (directory / "True").write_text(render(bootstrap(True)).replace("Upload Image", "Unexpected content"))
        try:
            capture(directory / "False", directory / "True")
        except ValueError:
            pass
        else:
            raise AssertionError("Capture accepted different templates")
        hostile = bootstrap(True)
        hostile["jobName"] = hostile["state"]["jobName"] = "</script><script>alert(1)</script>__TITLE____BOOTSTRAP__"
        safe = render(hostile)
        assert len(re.findall(r"<script\b", safe)) == 3
        assert json.loads(re.search(r"window\.__TICKET__ = (.*?);</script>", safe, re.S)[1]) == hostile
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", render(bootstrap(True)), re.S)
        assert len(scripts) == 3
        for index, script in enumerate(scripts):
            path = directory / f"inline-{index}.js"
            path.write_text(script)
            subprocess.run(["node", "--check", str(path)], check=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), PreviewHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        for path in ("/jobticket/", "/jobticket/DEMO01", "/jobticket/static/fonts.css", "/jobticket/static/fonts/inter-latin-400-normal.woff2"):
            with urlopen(base + path) as response:
                assert response.status == 200
                assert response.headers["X-Preview-Only"] == "no-storage-no-upstream"
                assert "connect-src 'self'" in response.headers["Content-Security-Policy"]
        for method, path, expected in (("PUT", "/jobticket/api/DEMO01", 405), ("POST", "/jobticket/api/DEMO01/image", 405), ("POST", "/jobticket/api/DEMO01/push", 405), ("GET", "/jobticket/api/DEMO01/sync", 405), ("GET", "/.git/config", 404), ("GET", "/jobticket/static/../ticket.html", 404)):
            try:
                urlopen(Request(base + path, method=method))
            except HTTPError as error:
                assert error.code == expected, (method, path, error.code)
            else:
                raise AssertionError((method, path, "Unexpected success"))
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
    print(f"PASS: {len(manifest['files'])} asset hashes, reusable template, safe JSON embedding, 3 JavaScript syntax checks, preview routes and API rejection")


if __name__ == "__main__":
    main()
