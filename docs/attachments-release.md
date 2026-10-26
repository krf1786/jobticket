# Material attachment release — October 26, 2026

Prepared for the approved direct attachments, with a 100 MB file limit. Publication
is pending; this section records completed local work only.

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
Python3.14/Starlette1.9; production Python3.11/Starlette1.6 rehearsal and live tests
are still pending. Runtime ticket/corkboard data has not been changed by tests.
