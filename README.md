# Job Ticket

This repository now includes a reusable capture of the frontend served by
[graphlab.info/jobticket](https://graphlab.info/jobticket/) on October 21, 2026.
It includes the editable red job number at upper left, its red mirror beside
the job name, server-save/upload client code, and conditional Teams-copy UI.

The working frontend is in [`frontend/ticket.html`](frontend/ticket.html), with
three reviewed save/reset/Teams fixes and the requested material-details columns
applied after capture. Material dropdowns now use about 28% of the editable
width, leaving most space for multiline **Material details**. A far-right
**Completed** checkbox saves per row and highlights it very light green. The exact original
capture remains in [commit `57f8f6b`](https://github.com/krf1786/jobticket/blob/57f8f6b28005d7511b67fc95c40b6bbd7695bd69/frontend/ticket.html).
See [review fixes and regressions](docs/review-fixes.md) and
[material details and compatibility](docs/material-details.md). The original
`jobticket.html`, `Job_Ticket2.html`, and `Job_Ticket3.html` remain unchanged as
historical standalone versions.

The verified deployed Python backend is now preserved in [`backend/`](backend/),
with narrow compatibility and PDF revision fixes. Runtime databases, uploads,
Microsoft credentials and ticket payloads are excluded. The approved frontend was published on October 22, 2026; the PR remains
unmerged. See the [frontend release record](docs/frontend-release.md). See [backend repairs](docs/backend-fixes.md) for
behavior, test evidence and the deployment boundary.

The latest [compact-row and Return-key follow-up](docs/material-row-release.md)
matches material row height to Production Steps and adds the next numbered row
when Enter is pressed in Material details (Shift+Enter inserts a newline).

## Local preview

Requires Python 3 (standard library only):

```sh
python3 scripts/preview.py --port 18765
```

- Scratch view: <http://127.0.0.1:18765/jobticket/>
- Synthetic saved view: <http://127.0.0.1:18765/jobticket/DEMO01>
- Synthetic Teams UI: <http://127.0.0.1:18765/jobticket/DEMO01?teams=1>

The preview binds only to loopback and never contacts the live service. It
rejects all API calls with HTTP 405 and stores nothing. Editing the synthetic
saved view will therefore show the existing save-error state. The Teams UI
example also requires mocked API responses for successful status or push
behavior. All demo values are invented. The scratch view remains unsaved.

The production template contains `__TITLE__` and `__BOOTSTRAP__` placeholders;
opening it directly as a file is not a supported saved-ticket preview.
Fonts are included locally, so no CDN is needed to render the preview.

## Verify and reproduce

```sh
# Python 3, Node.js and a Git clone with the capture commit; no external network calls.
python3 scripts/verify_capture.py

# Optional: reproduce from two existing, private local GET response files.
# Keep those responses outside the repository. No download or live API calls occur.
python3 scripts/capture_frontend.py /path/to/blank.html /path/to/saved.html \
  --output /tmp/ticket.html
git show 57f8f6b28005d7511b67fc95c40b6bbd7695bd69:frontend/ticket.html > /tmp/baseline-ticket.html
cmp /tmp/baseline-ticket.html /tmp/ticket.html
```

The capture script removes exactly the generated title and bootstrap JSON,
then requires both normalized responses to match. It does not print ticket
data. Compare re-captures with the immutable baseline, not the patched working
template. The manifest records both hashes separately.

See [source provenance and limitations](docs/source-provenance.md),
[frontend API expectations](docs/frontend-api-contract.md), and
[verification evidence](docs/verification.md).

## Deployment boundary

No installer, credentials, production database or automated deployment is included.
The running service uses a separate layout and does not deploy this PR on push.
Do not run historical installers or replace it with the preview server. Backend
repairs and frontend release are separate actions; see [backend documentation](backend/README.md)
and the [release record](docs/backend-release.md) for the verified scope.

Inter fonts retain their [OFL license](frontend/static/fonts/OFL.txt). Embedded
Tailwind 3.4.17 CSS retains its notice and [MIT license](frontend/TAILWIND-LICENSE.txt).
