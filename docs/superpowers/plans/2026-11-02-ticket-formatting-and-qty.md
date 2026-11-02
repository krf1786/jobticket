# Ticket formatting and material QTY Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development. Track steps below and preserve the ledger. Independent modules may be implemented in parallel with exclusive file ownership; integration/release stays sequential.

**Goal:** Provide selected-text formatting in all ticket prose fields and a compact saved per-material QTY column.

**Architecture:** Retain existing native plain-value controls as hidden adapters, with a safe contenteditable view and one shared toolbar. Persist whitelisted styled text runs alongside exact plain values; stable row IDs and acknowledged formatting baselines protect saved work. QTY remains a plain row-aligned value.

**Tech Stack:** Vanilla JavaScript/CSS, FastAPI, SQLite; existing Playwright/Python tooling, no new dependencies/CDNs.

**Spec:** `docs/superpowers/specs/2026-11-02-ticket-text-formatting-design.md` (approved, including QTY addition).

## Global Constraints

- Preserve existing ticket fields/images/100 MB attachments/material completion/Variable Data, header identity, row shortcuts, date defaults and serialized saving.
- Only VERIFY-MATERIALS-20261021 may receive live write tests; restore its exact original row/timestamps. Preserve customer tickets and shared-board data.
- No PR merge, access change, Graph/Teams setup or production dependency installation.
- Job number/date/due/time/main quantity remain native structured controls. Prose targets: jobName, notes, material name/details, production op/instr.
- Highlight palette: `#fef08a`, `#fbcfe8`, `#bbf7d0`. Allowed run keys: text, bold, italic, underline, size, color, highlight. Boolean marks, integer size 8–48 px, normalized six-digit hex colors.
- Formatting schema: `richText:{version:1,fields:{FIELD_KEY:RUNS}}`; concatenated run text must equal the corresponding plain field. Keys: `jobName`, `notes`, `material:ROW_ID:name`, `material:ROW_ID:details`, `production:ROW_ID:op`, `production:ROW_ID:instr`.
- `richTextBase` is request-only acknowledged prior richText (default `{version:1,fields:{}}`), stripped before storage. Stale baselines return409; explicit empty fields clear formatting.
- `productionRowIds` is a unique safe-ID array aligned with steps. Material IDs come from existing `row.materialRowId` and materialRowIds.
- `materialQuantities` is an array of blank or 1–9 digit nonnegative integer strings aligned with materials. Width accommodates two digits without imposing a two-digit maximum.

## Review Focus

- Selected emoji/multiline spans, mixed styles and formatting undo/redo preserve exact plain text.
- Toolbar focus, color/size controls, IME, paste/drop and keyboard/touch do not lose selection, import HTML or cause unrelated saves.
- Duplicate rows, omission by older tabs and a slow save acknowledgement do not silently erase styles or move QTY to another row.
- Default compact rows, material suggestions, details padding beside the paperclip and narrow screens remain usable.
- Print and corkboard visual snapshots show styles/highlights/quantities exactly once, with no formatting controls or truncated long text.

### Task 1: Validated persistence (independent backend module)

**Files:** create `backend/rich_text.py`, `tests/test_rich_text.py`; root integrates app.py and existing test isolation loaders.

**Interface:** `prepare_state(state:dict, previous:dict|None)->None`, called after attachments.prepare_material_fields and before any ticket write. It validates/normalizes richText, productionRowIds and materialQuantities, strips richTextBase and preserves safe legacy omissions. Raise FastAPI HTTPException400 for invalid input,409 for stale/ambiguous saves; no DB/files/network side effects.

- [x] Write failing tests for runs/plain equality, malicious keys/colors/sizes, Unicode, valid marks, exact false/empty clearing, stale baseline, stable production IDs, old-tab preservation/rejection, QTY alignment/validation and duplicate-row deletion.
- [x] Run with existing venv Python unittest; watch expected missing-module/behavior failures.
- [x] Implement prepare_state with bounded counts/text/runs, literal data only. Preserve omitted formatted fields only when associated exact text/identity still exists; reject ambiguous formatted-row changes. Preserve omitted QTY by safe IDs or unchanged arrays, reject ambiguous meaningful values.
- [x] Run tests and existing backend/storage tests; report results. Only own files may be committed.

### Task 2: Rich editing module (independent browser module)

**Files:** create `frontend/static/ticket-rich-text.js`, `frontend/static/ticket-rich-text.css`, `scripts/rich-editor-checks.js`; root integrates ticket.html.

**Interfaces:** expose `window.TicketRichText={mountAll(root=document),restore(state),collect(),acknowledge(sentState),sync(source),focus(source),isToolbarControl(target)}`. Native inputs/textareas marked `data-rich-key` remain in DOM with their IDs/value/row attributes, hidden only after mounting. Their visible sibling `.rich-editor[data-rich-key]` is the editing surface. `collect()` returns `{richText,richTextBase}`. restore reads state.richText, binds only exact matching plain strings, resets editing history; acknowledge uses only the sent snapshot, never newer edits. sync reflects programmatic source.value changes, clearing obsolete marks; focus targets visible editor.

- [x] Write/run failing standalone browser fixtures for exact strings/Unicode, selected bold/italic/underline/size/color/three highlights, collapsed typing, Clear Formatting, undo/redo, literal paste, selector focus and suggestions.
- [x] Implement safe text-node/span rendering and model/history. Never store or trust arbitrary HTML. Mount toolbar in `.toolbar` but keep it separate from status/Print. Toolbar controls must retain selection, expose accessible labels/states, support touch/narrow layouts and be hidden in print.
- [x] Synchronize source.value and emit one bubbling source input for actual text/format edits. Proxy Enter to the native source as a cancelable KeyboardEvent so existing row/header handlers run; if uncanceled, insert line break only for multiline editors. Keep native clipboard/selection editing safe and support IME.
- [x] Material sources with list=acrylicOptions expose an accessible suggestion picker using the same options. Hidden sources remain the plain contract; no transparent overlays. Hide obsolete plain print mirrors in rich hosts; formatted editor prints directly.
- [x] Run fixture checks; report exact API/selection/history limits and results. Only own files may be committed.

### Task 3: Ticket integration and QTY (root)

**Files:** modify `frontend/ticket.html`, `backend/app.py`, test loaders/preview scripts and appropriate current-source manifests; create `scripts/formatting-checks.py`.

- [x] Add backend import/call and isolation loader support for rich_text, then run Task1 and all existing backend tests.
- [x] Add QTY heading/input/print mirror (36px minimum desktop/print, 34px narrow); use explicit material-name selectors so the new numeric input cannot steal material identity. Add collect/restore/reset and row labels. QTY Enter adds next material row.
- [x] Load new CSS/JS before row initialization. Tag native prose sources with stable formatting keys after assigning/restoring row IDs. Mount new rows, restore full state after plain restoration, collect sidecar/IDs, acknowledge only sent snapshots, use visible-editor focus and ignore rich toolbar/view input events in generic autosave (source events save).
- [x] Verify real isolated API/browser save/reload, selected formatting across fields, quantity alignment/duplicate deletion, suggestions, Enter/newlines, files/completion/Variable Data/header/date regressions, legacy/stale save failures, undo/redo/paste, mobile and long formatted print. Adapt obsolete test selectors to actual visible editors rather than bypassing UI behavior.
- [x] Inspect screenshots/rasterized PDFs and current preview export. Update hashes and documentation after final code; commit verified source.

### Task 4: Independent review and release

- [x] Fresh reviewer checks full diff, spec, tests and Review Focus; fix important findings with failing/passing regressions.
- [x] Recheck production app/template/module/static/config hashes and health. Preserve newer corkboard module/config. Prepare guarded atomic replacement of only changed runtime code/assets, consistent DB backups, production compile and code-only rollback.
- [x] Publish exact verified commit, restart only for backend changes and verify normalized public source/health. Use only labeled synthetic fixture for live feature writes, guard final savedAt/state and restore original JSON/timestamps exactly. Audit all other tickets/attachments/board data.
- [x] Record release evidence, push feature branch and open/attach draft PR without merging. Final report distinguishes implementation/local/live verification and remaining limits.
