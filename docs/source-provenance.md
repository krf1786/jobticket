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
Reset cancellation, overlapping saves, and Teams push sequencing, plus the
subsequently requested material-details columns. It is no
longer byte-identical to the captured live template. The original baseline
remains addressable by its full Git commit; it is not replaced or rewritten.
See [review-fixes.md](review-fixes.md) and [material-details.md](material-details.md)
for scope and regression evidence.

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

## Deployed backend follow-up

Read-only inspection subsequently located `/root/jobticket` on the configured
VPS and verified the running service source. `app.py`, `graph.py` and `pdf.py`
matched the September 2 installer modules byte for byte. These reusable modules
were committed unchanged in `bdc201b2ca30085a4973eba48cfbc728b624cf65` before the
approved backend repairs. [backend-source-manifest.json](backend-source-manifest.json)
records the original and repaired hashes. No installer was executed.

The service is a single uvicorn worker behind the existing proxy. Its current
runtime versions were inspected, but no original dependency lockfile was found.
Database contents, uploaded images, credentials, environment files and generated
bootstrap payloads remain excluded. Graph configuration and the optional renderer
are absent in production; no Teams transport was performed or enabled.

The [backend release record](backend-release.md) separates the narrowly authorized
backend deployment/live synthetic persistence checks from local integration tests
and the still-unreleased frontend. It does not claim full Teams synchronization.

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

The production runtime modules/template are untracked in its separate checkout;
no Job Ticket polling/deploy job was found in the inspected service and root cron.
This work stays on `capture/live-frontend-2026-10-21` in an unmerged PR. `main`
is unchanged. Only separately authorized backend repairs may be deployed, as
recorded in [backend-release.md](backend-release.md).
