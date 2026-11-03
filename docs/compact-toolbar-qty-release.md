# Compact toolbar and QTY controls — November 2, 2026

Source `476e9a8b2a97923f3417bb21e4af787b461a46d3` is live. Print and Saved
share a row, with formatting directly below; the desktop toolbar decreased from
131.5px to79px. QTY is now the first material column, with visible up/down
buttons and keyboard ArrowUp/ArrowDown support. Values remain with their rows,
clamp at0/999999999 and do not save unchanged boundary clicks. The buttons do
not increase the compact21px desktop material-row height.

Only ticket.html and static/ticket-rich-text.css were atomically replaced at
**2026-11-02 23:59:12 UTC** (6:59 PM New York), CSS first. Source hashes,
public normalized scratch/saved HTML, public CSS, health and the unchanged
service PID were verified. Both online SQLite backups passed integrity checks,
including WAL content; every existing row remained unchanged. No service
restart, backend/module change, dependency/config/credential change or Graph
integration work occurred. All16 other runtime modules/assets were preserved.

## Verification

- 52 focused isolated API/SQLite/browser checks passed: toolbar geometry, QTY
  placement, buttons/keyboard, limits/no redundant writes, exact persistence,
  independent rows, deletion/renumbering, formatting, original attachment bytes,
  completion, Variable Data, scratch, mobile and print.
- All50 existing formatting integration checks and source/hash/syntax/bootstrap/
  preview safety checks passed. Unchanged backend tests were not rerun.
- Rendered desktop/mobile/print artifacts were inspected. At320px, Details have
  61px usable text width and the complete Done heading fits. Print renders the
  quantity once and hides buttons; SVG ticket exports hide the new buttons.
- Independent review found no actionable issues.

All **16 public live checks** passed, with one PUT solely to the labeled
VERIFY-MATERIALS-20261021 fixture. Buttons and keyboard produced exact saved
quantities12/2; reload, desktop/mobile layout and browser print were verified.
No browser errors or unauthorized requests occurred. The exact original row,
JSON and timestamps were restored at **2026-11-03 00:00:40 UTC** (7:00 PM
November2 in New York), guarded by the successful savedAt/exact expected state.
All25 ticket rows, attachment records and corkboard data were unchanged.
These are local/live checks, not GitHub CI or bot approval. Production
Graph/renderer remain disabled and Teams/PDF delivery is unverified.

## Sources and rollback

- ticket.html: `3ce3f67266414af0c4622e93d45d5d6d289d23d481097da0294b22ba04ae718a`
- static/ticket-rich-text.css: `8d46407604002088b9f8825bdfceb5e120d70b91371d671e9326b41bb9453b57`

Private code/database backups, row fingerprints and release receipt are in
`/root/jobticket/release-backups/compact-20261102T235901Z-7c8f88b0/`.
The exact synthetic fixture audit is in the separate
`compact-test-20261102T235954Z-19f87656/` folder. Code-only rollback was prepared
and not invoked:

```sh
/root/jobticket/venv/bin/python -B /root/jobticket/release-backups/compact-20261102T235901Z-7c8f88b0/rollback.py
```

It refuses unknown revisions/config, restores HTML then CSS, preserves current
database/attachment data and verifies the same service PID. No database restore
or restart is performed. No PR was merged; GitHub push/merge does not deploy.
