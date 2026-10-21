# Verification — October 21, 2026

All interactions used synthetic local data. No live API write, upload, Teams
push, or new-ticket navigation was performed.

## Source and offline checks

`python3 scripts/verify_capture.py` passed:

- All seven captured template/asset/license SHA-256 hashes match the manifest.
- Scratch and synthetic saved renderings recover the same reusable template.
- Capture refuses responses differing outside the title and bootstrap.
- Template rendering safely handles closing script tags and placeholder-like
  text in job names without corrupting the bootstrap.
- Node syntax checks pass for all three rendered inline script blocks.
- Preview pages and local assets return 200 with same-origin connection policy.
- Save, upload, Teams push, and sync API routes return 405.
- Requests for `.git/config` and paths outside the asset allowlist return 404.

`node --check scripts/browser-checks.js` passed. Re-capturing the two original
responses into a temporary file and comparing with `frontend/ticket.html`
produced no differences. The three original HTML variants match the base
commit byte for byte.

## Browser checks

Playwright Chromium completed **22 checks**, with **11 mocked API requests**,
**0 JavaScript page errors**, and **0 external requests attempted**. The test
blocks non-local requests before navigating and intercepts all API traffic.

Coverage includes scratch edits without saving; no saves during bootstrap
restoration; both number displays sourced from `jobId`; computed 46px/26px
sizes and `rgb(239, 68, 68)` color; number mirroring, normalization and navigation;
job-name number extraction; material row insertion; state collection and
autosave; multipart image upload and URL persistence; failed-save feedback;
Teams readiness gating, mocked status, push success and failure; reset; and
print visibility of both numbers with the toolbar hidden.

The saved-view screenshot was visually reviewed. A print PDF was generated.
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

The staged diff contains only new capture, asset, documentation, and local
verification files. No historical HTML is modified. A targeted scan found no
private keys, GitHub tokens, AWS access keys, JWTs, assigned client/API secrets,
or generated `window.__TICKET__` payloads in the added text files. The captured
source was also reviewed directly. No credentials, environment files, raw live
responses, database, uploads, browser state, or session configuration are added.
