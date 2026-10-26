# Material Attachments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one saved, downloadable attachment per material row, up to 100 MB.
**Architecture:** Existing FastAPI/SQLite owns opaque attachment metadata and streamed files; stable row IDs and aligned metadata travel with the existing ticket JSON. Browser controls live in the material-details cell. Keep the deployed corkboard baseline unchanged.
**Tech Stack:** Existing Python/FastAPI/SQLite and inline browser JavaScript; no new dependencies.
**Spec:** docs/superpowers/specs/2026-10-26-material-attachments-design.md

## Global Constraints

- One file per row; maximum 104,857,600 bytes; zero-byte files are allowed.
- Download-only delivery, validated job ownership, opaque file IDs, no paths from filenames.
- Preserve existing data and corkboard integration. Live writes only to VERIFY-MATERIALS-20261021, with exact restoration.
- No Graph/Teams setup, dependency installs, automatic file deletion or PR merges.
- Current ticket access remains unchanged; no new authentication promised.

## Review Focus

- Failed replacement and row deletion during upload retain correct surviving state.
- Duplicate material names and older clients cannot silently move or erase attachments.
- Exact maximum succeeds; maximum plus one is rejected without partial stored files.
- Hostile names/metadata and cross-job IDs cannot escape storage or execute in the browser.
- Empty rows remain compact; Enter activates file controls instead of creating a material row.

### Task 1: Backend storage, download and compatibility (delegated)

**Files:** backend/attachments.py, backend/app.py, tests/test_attachments.py, tests/test_backend.py.
**Consumes:** Existing FastAPI app, DB_PATH, PREFIX, get_ticket and material JSON arrays.
**Produces:** POST /jobticket/api/{job}/attachments -> {ok:true,file:{id,name,size,url}}; GET /jobticket/api/{job}/attachments/{id} -> original file download. State fields materialRowIds:string[] and materialFiles:(null|metadata)[] aligned with materials.

- [x] Write real isolated HTTP/SQLite tests; prove new upload/download and legacy protections fail before implementation.
- [x] Implement streaming bounds, canonical registry metadata, safe downloads, stable-ID validation and omission protection.
- [x] Adapt existing isolated test harnesses to include deployed corkboard/new module; run unittest discovery.

### Task 2: Row controls and browser integration (root)

**Files:** frontend/ticket.html, scripts/preview.py, scripts/verify_capture.py, scripts/verify_backend.py, scripts/attachment-checks.py.
**Consumes:** Task 1 HTTP contract and canonical metadata; the existing serialized save queue.
**Produces:** Attach/Download/Replace/Remove UI, stable IDs in collect/restore, pending-upload unload protection and printable names.

- [x] Write browser tests against a real isolated backend; demonstrate missing attachment behavior.
- [x] Implement compact controls, size validation, upload generation guards, failed-replacement retention and row-safe persistence.
- [x] Test exact bytes and saved reload, keyboard, scratch behavior, duplicate rows, removal, failure and print.
- [x] Run current frontend suites and real backend integration; inspect rendered desktop/mobile/print.

### Task 3: Review and release

**Files:** manifests, attachment release documentation, guarded release/audit scripts outside Git.

- [ ] Obtain independent code/data-safety review and fix material findings.
- [ ] Back up current app/template and consistent SQLite, verify expected deployed hashes, stage and atomically publish changed runtime files, restart and check health; prepare guarded rollback.
- [ ] Verify one restored synthetic ticket upload/download/save/reload and the actual 100 MB boundary without touching customer tickets. Compare all customer rows.
- [ ] Record honest evidence and push a separate unmerged PR based on the existing frontend branch; preserve original dirty checkout.
