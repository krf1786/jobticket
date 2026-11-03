# Formatter icons — November 2, 2026

Source `1e7f2f88145ee93f18aaed0822b5ecd65c753eac` is live. Word labels were
replaced with B/I/U glyphs, an A/current-color underline, three colored
highlighter symbols and a Clear Formatting T/eraser icon. Tooltips and accessible
names remain unchanged. The native color input stays focusable/clickable, and
the desktop controls fit on one45px row; phone layouts wrap at79/111px for
390/320px viewports. Font size initially displays10 and follows the selection.

Only ticket.html and its formatting JS/CSS changed. They were backed up and
atomically published CSS → JS → HTML at **2026-11-03 00:21:45 UTC** (7:21 PM
November2 in New York). Both database backups passed integrity checks. Public
normalized HTML/static hashes, health, all existing rows, protected code/config
and unchanged service PID were verified. No restart/backend/schema/dependency/
credential/Graph change occurred. All15 other runtime modules/assets remain
unchanged.

## Verification

- 63 focused isolated real API/browser checks passed: seven icon actions,
  names/tooltips/decorative accessibility, native color pointer/keyboard target,
  focus feedback, current-color underline, selection retention and every mark,
  numeric size, zero render/reload saves, QTY controls, responsive layout, print
  and actual SVG preview. Desktop/phone/print screenshots were inspected.
- Existing editor fixture and all50 formatting integration checks pass. Source
  hashes, script syntax, bootstrap safety and preview routes pass. Initial font10
  was additionally verified with zero writes and a refreshed toolbar screenshot.
- Independent review approved the presentation-only change. The formatting
  model/history/persistence contract remains unchanged.
- All22 public live browser checks passed, including each icon action and three
  saved-palette colors, size/color, Clear, color underline, narrow layouts, QTY
  arrow visibility and print. Live interaction used only the scratch page, with
  zero API write requests, blocked requests or browser errors.

A read-only audit confirmed all25 ticket rows, attachment records and corkboard
data unchanged. No saved-ticket fixture was edited, so no data restoration was
needed. These checks are not GitHub CI/bot approval. Production Graph/renderer
remain disabled; Teams/PDF delivery remains unverified.

## Runtime and rollback

- ticket.html: `dd40796aba5790b999276c9c043a28dd1d8d5c621f38e1abd327813e437da2a9`
- static/ticket-rich-text.js: `6243345ba4c3f2533b82357d5da431a21096c3f593b1cccd38ba3ad740b85bd1`
- static/ticket-rich-text.css: `bfdf4946c9a155157d9bacfc7b3d38e527402624777c0e9ae32059a3acd89b3b`

Private source/database backups, staged code, row fingerprints and receipt are in
`/root/jobticket/release-backups/icons-20261103T002126Z-3e399e27/`.
Guarded code-only rollback was prepared and not invoked:

```sh
/root/jobticket/venv/bin/python -B /root/jobticket/release-backups/icons-20261103T002126Z-3e399e27/rollback.py
```

It restores HTML → JS → CSS only after revision/config guards, retains current
database/attachment data and verifies the same service PID. It does not restart
or restore data. No PR was merged; GitHub push/merge does not deploy this app.
