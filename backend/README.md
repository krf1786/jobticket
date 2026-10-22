# Verified backend source

These modules were copied from the running service after read-only inspection.
The original baseline is commit `bdc201b2ca30085a4973eba48cfbc728b624cf65`;
[the manifest](../docs/backend-source-manifest.json) distinguishes repairs.
No credentials, database, uploads or runtime state are included.

The service expects `app.py`, `graph.py`, `pdf.py`, `ticket.html` and `static/`
together in one runtime directory. It creates SQLite storage and upload/static
directories there. Importing `app.py` starts its sync worker. Do not import it
from a real runtime directory for tests. The test harness copies source to a
temporary directory and suppresses that worker.

The inspected production environment runs Python 3.11.15, FastAPI 0.141.1,
uvicorn 0.52.4 and python-multipart 0.0.32, with one uvicorn worker. There was no
verified original dependency lockfile. PDF generation optionally uses Python
Playwright and Chromium; those dependencies and Graph configuration are currently
absent in production. This repository does not install or configure them.

Run the isolated unit suite in an environment with the API dependencies:

```sh
python -m unittest discover -s tests -v
```

The optional full integration check also requires `httpx`, `pypdf`, Python
Playwright and its Chromium browser:

```sh
python scripts/verify_backend.py
```

That check uses only loopback HTTP, a fresh synthetic SQLite database, the
candidate template and intercepted Graph transport. It writes PDFs and its JSON
report under ignored `output/backend/`. No production API or Teams transport is
called. The regression suite can reproduce the original defects by setting
`JOBTICKET_BACKEND_SOURCE` to a temporary checkout of the three baseline modules.

Deployment is separate from Git push. See [repairs](../docs/backend-fixes.md)
and [release evidence](../docs/backend-release.md).
