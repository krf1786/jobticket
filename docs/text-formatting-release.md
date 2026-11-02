# Text formatting and material QTY — November 2, 2026

The formatting toolbar and compact material QTY column are live. Selected text
supports bold, italic, underline, size, color, yellow/pink/green highlighting and
Clear Formatting in all six prose categories. Quantities save with their stable
material rows. Plain text, existing attachments and other ticket fields remain
compatible; stale/ambiguous older saves reject instead of discarding new data.

Final runtime source: `54f6cd0a4d8f1854a46db33416fef6d8b082c977`.
The five-file release from `6cacd633956bf100b1f9907a8bd05ff488a80a5b` was published
at **23:27:27 UTC** (6:27 PM New York), with consistent integrity-checked backups
of both databases and a verified restart/healthy normalized public source at
23:27:30 UTC. A later SVG-rendering check found the toolbar visible in exported
thumbnails; a minimal CSS correction from the final source was backed up and
atomically published at **23:31:59 UTC**, without restart. An actual exported SVG
regression and scoped independent review confirmed the correction. The updated
private receipt preserves the initial source and both CSS hashes; its guarded
full-release code-only rollback recognizes the final revision.

## Verification

- 63 backend/storage tests, including exact runs/plain values, malformed input
  without writes, safe legacy repair, row identity, quantities and stale saves.
- Standalone editor browser fixture: selection, inherited styles, collapsed
  typing, undo/redo, Unicode, literal paste, synthetic IME, readable highlights,
  mixed multiline sizes, toolbar state, shortcuts and suggestions.
- 50 real isolated API/SQLite/browser workflow checks, including duplicate rows,
  pending-save acknowledgement, failure/recovery, QTY validation, mobile/touch
  emulation, complete long PDF output and actual SVG preview rendering.
- 60 existing save/header/date/image scenarios and 24 Variable Data checks.
  Source/asset hashes, script syntax, bootstrap escaping and preview safety pass.
- Desktop/mobile screenshots and rasterized local PDFs were inspected. Small
  phone Details have 68px usable text width at320px and116px at390px; empty
  desktop Material/Production rows remain21/20px respectively.

All **22 public live checks** passed with zero browser errors, blocked requests
or failed writes. One serialized PUT updated only the labeled
VERIFY-MATERIALS-20261021 fixture. It covered all prose categories, three
highlights, mixed style/size/color, Clear Formatting, QTY12/7, exact reload,
preserved header identity, mobile layout and print. Desktop/mobile/print evidence
was inspected. The exact fixture JSON and original timestamps were restored at
**23:33:11 UTC**, guarded by its successful savedAt and exact expected final state.
All 25 ticket rows, attachment records and corkboard data remained unchanged.

Independent review findings for malformed input, formatting history, large-font
line height, header identity and invalid-QTY feedback were fixed and regression
tested. These are local/live verification results, not GitHub CI or bot approval.
Physical OS IME/hardware touch was not tested. Corkboard thumbnails retain their
existing first-Letter-page crop; full longer tickets remain available expanded.
Production Graph/PDF/Teams delivery remains disabled and unverified.

## Runtime and rollback

Only app.py, ticket.html, new rich_text.py and two new rich-text static assets
changed. Newer live corkboard source, all13 protected modules/assets, Caddy,
service configuration, credentials and dependencies were retained.

- app.py: `cd819a1fea6c4adb2512ac537446e2927a687c68ef24394b07ee4c47806bccad`
- ticket.html: `57fed31e7da85552443347c319841e8dbe227098a3347fe6de985637ab19eabd`
- rich_text.py: `44b943a9db6780b50332fd75d1a280724cf41bd3db3c6812675a68473ed0a75a`
- static/ticket-rich-text.js: `99ae724d4f612d3d93df43309e3519acbd76f98835fa1adadcfc707be026fb48`
- static/ticket-rich-text.css: `19ef9f5ee48525592c02e86f34657483b3c3d23dcb9875a068db7d0bdb70099e`

Private backups, receipts, staged/compiled code and guarded rollback are in
`/root/jobticket/release-backups/formatting-20261102T232720Z-f628e01f/`.
The owned fixture's private snapshot/restoration record is separately in
`formatting-test-20261102T233247Z-06ad2d65/`. Rollback was not invoked:

```sh
/root/jobticket/venv/bin/python -B /root/jobticket/release-backups/formatting-20261102T232720Z-f628e01f/rollback.py
```

It guards code/config revisions and restores/removes only the five feature code
files, then restarts/verifies health. All current database/attachment data remain
in place. Never restore a database backup over newer user work automatically.
No PR was merged. GitHub push/merge does not deploy the service.
