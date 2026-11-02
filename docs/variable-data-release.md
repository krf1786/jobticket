# Variable Data release — November 2, 2026

The blank checkbox beside Job Information is live. Checking it shows bold green
Variable Data text to the right of the box; unchecking hides the text. Saved
tickets retain the boolean through autosave/reload, and older tabs that omit it
cannot clear the setting. Scratch tickets remain unsaved.

Runtime code is from `16fa549cfda586e793c8d9a335d1c4efa2a62f59`.
Only `app.py` and `ticket.html` were atomically replaced at **21:19:35 UTC**
(4:19 PM New York), followed by a verified restart. Both databases were backed
up consistently while stopped and passed integrity checks. Deployment health,
public scratch/saved normalized template hashes and all existing rows were
verified at **21:19:38 UTC**.

## Validation and preservation

- 43 backend/storage tests, including three new Variable Data regressions.
- 24 focused real isolated API/SQLite/browser checks: exact true/false saves,
  reload, older tabs, keyboard, scratch, 1200/390/320px layout, adjacent data,
  attachment bytes and both printed states.
- 45 existing frontend/save/material browser scenarios and source/syntax/preview
  checks. Desktop/mobile screenshots and rasterized Letter PDFs inspected.
- 16 live checks with exactly two public PUTs, both to the labeled
  VERIFY-MATERIALS-20261021 fixture. No browser errors or unauthorized requests.
  The fixture was restored exactly, including original JSON bytes/timestamps,
  at **21:20:28 UTC** after matching its successful save revision and expected
  final state. All 25 ticket rows, attachment registry and corkboard data were
  unchanged after cleanup.

The live corkboard backend is newer than the historical copy in this checkout.
Its current SHA-256 `38020eb0169aad4c9448ad3fa6eb33d06f1c4705c2c2a9c0f55d1f5e3f046ba8`
was guarded and preserved. All 13 other runtime modules/assets, current Caddy
configuration and the service unit were retained. No dependency, credentials,
Graph/Teams settings, attachment bytes or access policies changed. Production
Graph/renderer remain disabled; production PDF/Teams delivery is unverified.
These results are local/live verification, not GitHub CI or bot approval.

## Sources and rollback

Runtime SHA-256:

- app.py: `be82c24344b99c000195c909958154c8449ae9b27e3ee3f0b5f81ec361b7e41f`
- ticket.html: `c919a65b677f2efe029800e06f054cc9631dea48ec9fcb71940e534f839a47e8`

Private code backups, consistent database backups, staged/compiled sources,
row fingerprints, release receipt and guarded rollback are in
`/root/jobticket/release-backups/variable-data-20261102T211931Z-9aa0300a/`.
Fixture evidence is in the separate private
`variable-data-test-20261102T212007Z-a36e70bc/` backup folder.

Rollback was prepared and not invoked:

```sh
/root/jobticket/venv/bin/python -B /root/jobticket/release-backups/variable-data-20261102T211931Z-9aa0300a/rollback.py
```

It refuses unknown code/config revisions, restores only the two original code
files and restarts/verifies health. It retains current database and attachment
data. Never restore a database backup automatically over newer user work.
No PR was merged; GitHub push/merge does not deploy the app.
