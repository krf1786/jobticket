# Material attachment release — October 26, 2026

Direct attachments with a 100 MB file limit are live. Runtime code is from
`31d7de0c1555c879a64dca5ae64543be7e34a7a1`.

The feature adds per-material Attach/Download/Replace/Remove controls, stable row
identity, canonical job-owned file metadata, original-byte downloads, bounded
multipart/storage reads, stale-client protection and plain printed filenames.
The existing corkboard integration was copied byte-for-byte from the inspected
live baseline into an isolated checkout; the original dirty working copy remains
untouched. No Graph configuration, dependency installation or PR merge occurred.

Local verification passed:

- 40 backend/storage tests, including exact100 MiB and one-byte-over limits,
  request-body bounding, failure cleanup, metadata/path ownership, stale clients,
  file permissions, hostile filenames/bootstrap rendering and all17 legacy tests.
- 31 real isolated browser/API/SQLite checks: bytes, persistence, duplicate rows,
  failed replacement, deletion during upload, pending-save races, two-tab409,
  keyboard behavior, compact rows, mobile filename layout, print and corkboard.
- All92 existing frontend scenarios, including35 image-viewer checks.
- All40 existing real backend/API/SQLite/PDF integration checks; external Graph
  transport was intercepted and production Teams delivery remains unverified.
- Source hashes, three inline and two external JavaScript syntax checks,
  bootstrap safety and preview API rejection.

Desktop/mobile screenshots and a rasterized Letter PDF were inspected. Review
identified and resolved early multipart bounding, a valid special row-ID baseline
case, safe template-token filenames and plain printed names. Local tests use
Python3.14/Starlette1.9. The production Python3.11/Starlette1.6 rehearsal also
passed all seven checks, including an actual100MiB multipart upload, full
download SHA-256, one-byte-over rejection with no partial metadata/bytes/spool,
and the unchanged corkboard router. No production API writes occurred during
that isolated rehearsal.

## Publication and live verification

Published by guarded atomic replacement at **2026-10-26 23:11:23 UTC**
(7:11 PM New York time), followed by a verified service restart. Only app.py,
new attachments.py, ticket.html and new static/material-attachments.js changed
at runtime. Graph/PDF modules, corkboard source/static, Caddy and service
configuration remain unchanged. Both SQLite databases were backed up consistently
while stopped, and each backup passed its integrity check.

All **18 live checks** passed through the public HTTPS service: saved row controls,
original-byte browser downloads, replacement/removal, reload, keyboard, mobile,
print, an exact104857600-byte upload/download, saved file metadata, and rejection
of104857601 bytes without changing the existing attachment. Only the labeled
VERIFY-MATERIALS-20261021 ticket was written. Cleanup restored its exact original
row, including timestamps, and removed only owned synthetic upload records/bytes.
The final audit at **23:14:40 UTC** confirmed all18 ticket rows and corkboard data
unchanged, with no browser errors or unauthorized requests. The first cleanup
audit hit a test-helper SQLite-row serialization error; it was corrected, the
fixture restored exactly, and the full live verification/cleanup rerun passed.

Runtime SHA-256:

- app.py: `f6838435b3cf01c784987f260db25a37c14b5379c0fb7b6d419450a94adba047`
- attachments.py: `a470635ef841b7a79203628c204dfd9991ebbcfe75ddc1331cbd1b7418a766f8`
- ticket.html: `2dc3fd4e1b0b0741ec7e00ca4af249509ffd64f5590196bd5100d4a0648f80d5`
- material-attachments.js: `449e2b04dd8dcf5f2ab888f1c0f6c267778aad674d68d36fc70e07dad465cbd2`

Private receipts, previous code, consistent tickets.db/corkboard.db backups and
guarded rollback are in:
`/root/jobticket/release-backups/attachments-20261026T231040Z-b6b22a63/`.
Rollback was prepared but not invoked:

```sh
/root/jobticket/venv/bin/python -B /root/jobticket/release-backups/attachments-20261026T231040Z-b6b22a63/rollback.py
```

It refuses unknown code/config revisions and restores code only, including safe
handling of a partial installation. It retains both databases and attachment
bytes and verifies health after restart. Never restore a database backup over
newer user changes automatically. Graph/production PDF delivery remains disabled
and unverified. The original dirty checkout is untouched; the new source is in
`/Users/kylefleming/Documents/Codex/2026-10-26/jobticket-material-attachments` on
`codex/material-attachments-100mb`. PR #2 remains unmerged; attachment work uses a
separate unmerged review branch based on it. Git push/merge does not deploy.
