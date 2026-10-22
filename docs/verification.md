# Verification — October 21, 2026

The frontend checks below use synthetic local data. The subsequent approved
backend repair and synthetic live persistence test are separately recorded in
[backend-release.md](backend-release.md); no Teams delivery is claimed.

## Source and offline checks

`python3 scripts/verify_capture.py` passed:

- The original captured template at commit `57f8f6b` matches its immutable hash.
- All seven current template/asset/license SHA-256 hashes match the manifest.
- Scratch and synthetic saved renderings recover the same reusable template.
- Capture refuses responses differing outside the title and bootstrap.
- Template rendering safely handles closing script tags and placeholder-like
  text in job names without corrupting the bootstrap.
- Node syntax checks pass for all three rendered inline script blocks.
- Preview pages and local assets return 200 with same-origin connection policy.
- Save, upload, Teams push, and sync API routes return 405.
- Requests for `.git/config` and paths outside the asset allowlist return 404.

`node --check` passed for all three browser scripts. Re-capturing the two original
responses and comparing with `frontend/ticket.html` at commit `57f8f6b`
produced no differences. The working template now includes the three documented
review fixes and the requested material-details columns. The three historical HTML variants still match the original
repository base commit byte for byte.

## Browser checks

After adding material details, Playwright Chromium again completed **22 existing checks**, with **11 mocked API requests**,
**0 JavaScript page errors**, and **0 external requests attempted**. The test
blocks non-local requests before navigating and intercepts all API traffic.

Coverage includes scratch edits without saving; no saves during bootstrap
restoration; both number displays sourced from `jobId`; computed 46px/26px
sizes and `rgb(239, 68, 68)` color; number mirroring, normalization and navigation;
job-name number extraction; material row insertion; state collection and
autosave; multipart image upload and URL persistence; failed-save feedback;
Teams readiness gating, mocked status, push success and failure; reset; and
print visibility of both numbers with the toolbar hidden.

The cancellation and timing suite again completed **12 regression cases**
with zero failures, page errors, or external requests. Each defective behavior
was observed failing before its fix; the confirmed Reset case served as a
passing control. [Review-fix evidence](review-fixes.md) records the successive
red/green results and reproducible command. Browser timing is controlled with
[Playwright Clock](https://playwright.dev/docs/clock), and HTTP responses are
released explicitly rather than relying on network speed.

The new material-details suite completed **6 scenarios** after all six failed
on the pre-change template. It covers old tickets, multiline entry, save and
restore, aligned row deletion, Reset cancellation, waiting for save before
Teams push, scratch behavior, 320px/390px layout, and literal-text print wrapping.
It reported zero failures, page errors, or external requests. See
[material-details.md](material-details.md) for commands and the additive state
contract. The 40 total browser checks/scenarios use no real backend writes.

The desktop, narrow-screen, and print screenshots were visually reviewed.
A local print PDF was generated.
These contain only the synthetic `DEMO01` ticket, not the production reference.
Generated artifacts remain under ignored `output/playwright/`.

To reproduce with Playwright CLI installed:

```sh
# Terminal 1
python3 scripts/preview.py --port 18765

# Terminal 2 — use a fresh named session
mkdir -p output/playwright
playwright-cli -s=jobticket-check open about:blank
playwright-cli -s=jobticket-check --raw run-code \
  --filename=scripts/browser-checks.js
playwright-cli -s=jobticket-check close
```

The preview is intentionally not a backend implementation. Mocked success
responses verify the captured frontend's handling, not production persistence
or Teams/SharePoint integration.

## Publication review

The PR contains the source capture, assets, documentation, local verification,
the three scoped client fixes, the material-details UI/state change, and the
subsequently verified backend source/repairs with isolated regression tests.
No historical HTML is modified. A targeted scan found no
private keys, GitHub tokens, AWS access keys, JWTs, assigned client/API secrets,
or generated `window.__TICKET__` payloads in the added text files. The captured
source was also reviewed directly. No credentials, environment files, raw live
responses, database, uploads, browser state, or session configuration are added.

## Completion follow-up — October 22, 2026

The current candidate narrows Material to about 28% of editable width and adds
far-right completion checkboxes, light green row highlighting and a parallel
boolean state array. The material suite now has 10 scenarios; together with the
22 existing checks and 12 save/reset/Teams races, the frontend total is 44.
Backend coverage is 17 unit regression methods and 40 isolated integration
assertions with real HTTP/SQLite/browser/PDF paths. External Graph transport is
intercepted. Four-page output retains all 180 long-detail lines; a separate PDF
assertion verifies checked and unchecked marks independently of row color.

The approved backend-only deployment and 14 live synthetic persistence checks
subsequently succeeded. [The release record](backend-release.md) separates those
results from mocked frontend tests and intercepted local Graph transport. The
frontend itself remains unpublished and Teams remains disabled.
