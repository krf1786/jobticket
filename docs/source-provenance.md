# Source provenance

Captured October 21, 2026, from read-only HTTP GET responses for:

- <https://graphlab.info/jobticket/> — scratch mode, `saving: false`.
- <https://graphlab.info/jobticket/sb0000> — the user-provided existing saved
  reference, `saving: true`, `sync.ready: false` at capture time.
- `/jobticket/static/fonts.css` and the three Inter WOFF2 files it references.

In the original capture commit `57f8f6b28005d7511b67fc95c40b6bbd7695bd69`,
only the generated page title and `window.__TICKET__` JSON were replaced with
the original template markers `__TITLE__` and `__BOOTSTRAP__`. The two resulting
templates were byte-identical. All other HTML, inline JavaScript, embedded CSS,
labels, print styles, and client behavior were retained without refactoring.
The static `SB0000` input placeholder is part of the live template; no ticket
ID, customer data, image URL, sync state, or configuration is embedded as a
runtime payload. The local preview uses a separate synthetic `DEMO01` fixture.

[`source-manifest.json`](source-manifest.json) records original response hashes,
asset origins, capture time, the immutable original template commit/hash, and
the current checked-in file hashes. Raw responses are not committed. The
scripts perform no live requests.

The working `frontend/ticket.html` now includes three user-approved fixes for
Reset cancellation, overlapping saves, and Teams push sequencing. It is no
longer byte-identical to the captured live template. The original baseline
remains addressable by its full Git commit; it is not replaced or rewritten.
See [review-fixes.md](review-fixes.md) for scope and regression evidence.

## Local source investigation

The existing June 2 local workspace held an older standalone HTML version.
A local `install-jobticket.sh`, modified September 2, 2026, contained heredocs
for `ticket.html`, `app.py`, `graph.py`, `pdf.py`, font CSS, and environment setup.
It was read as source and **never executed**.

Its template predates the live dual-red-number enhancement: the current served
template adds the 46px red editable number, the 26px right-hand mirror, number
normalization/navigation, job-name number extraction (comment dated
`2026-09-02`), and moves the print date into the footer. This local source
confirmed the original template markers and provided historical context for
API behavior. It was not treated as the currently deployed backend.

No matching current server checkout was found in the relevant local project,
older Job Ticket workspace, or named Job Ticket downloads inspected. Hidden
session stores were not searched. This is a bounded source search, not proof
that no other copy exists.

## Missing source and verification limits

- Current deployed backend source, dependency lockfiles, service/proxy config,
  and deployment mechanism have not been obtained or verified.
- Microsoft Graph/Teams/SharePoint credentials, job folder mappings, and
  production PDF rendering are outside this capture.
- Database contents, uploaded images, real ticket state, and generated runtime
  bootstrap JSON are deliberately excluded.
- No save, image upload, Teams push, sync polling, or new job route was exercised
  on production. Browser interactions used only localhost and mocked responses.
- `sync.ready: false` on the reference means Teams UI was gated off there.
  Mocked UI checks do not establish live Teams integration health.

The original commit preserves the frontend as observed. The current branch
adds only the documented client fixes; it is not a redesign, backend
reconstruction, production release, or claim of full backend synchronization.
In scratch mode the save layer returns early, so saved-mode
number initialization and navigation handlers do not run. Saved-mode API
calls remain tied to bootstrap `jobId` until navigation, even while the number
field is edited. Those behaviors are carried forward unchanged.

## Repository and deployment inspection

Base: `ce6d1142c7a4b9a0e1aedcd2b0525c3cb9692a56` on `main`.
The tracked tree contained only three HTML files. Read-only GitHub checks on
October 21 found no Actions workflows, no webhooks, no recorded deployments,
and no GitHub Pages site. No tracked deployment configuration was present.
Repository Actions were enabled but had no workflows to execute.

External server-side polling cannot be ruled out from repository metadata.
The capture is therefore proposed on `capture/live-frontend-2026-10-21` in an
unmerged PR; `main` and the running service are not updated by this work.
