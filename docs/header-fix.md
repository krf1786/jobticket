# Red job-number initialization repair

Investigation after the material-layout release found that the header markup and
September 2 number handlers were identical to the immutable capture and the
pre-release template. Read-only live inspection showed both 46px/26px red numbers
working on `/jobticket/sb0000`, with no browser errors or attempted writes.

The blank `/jobticket/` page returned early when `saving` was false, before any
header handlers were registered. Its left input was empty with a gray placeholder,
and its right mirror stayed empty even after an SB number was typed in the job
name. This defect was inherited from the captured source; the material-layout
change did not remove the header. Existing tests covered the saved-page header
but missed scratch header interaction. Saved headers intentionally start from the
actual bootstrap job ID; a stored job name can mention a different SB number and
must not silently replace it.

## Scoped repair

Header initialization now runs independently of persistence. Scratch mode binds
job-name extraction and manual-number mirroring but remains unsaved: typing or
pressing Enter there does not save or create a ticket. The empty left placeholder
uses the existing red color; the right number appears when a real number is entered.
No placeholder is treated as an actual ticket identity.

Saved mode initializes both numbers from the actual bootstrap job ID after
reload, even when the restored name mentions another number. Typing a name
containing `SB4321`, `SB 4321` or `SB-4321` fills both corners in uppercase. Direct
number edits update the right mirror. The existing saved-page Enter navigation
remains intact. Save requests remain bound to the current bootstrap job ID until
navigation; this repair does not silently save another ticket.

Original positions, 46px left / 26px right sizes, and `#ef4444` color are retained.
Materials/details, Completed controls, backend protections and Teams gating are
unchanged. The original long-identifier input-width behavior is outside this fix.

## Regression evidence

`scripts/header-checks.js` adds six focused scenarios. Before the repair, four
failed for scratch initialization and the initial candidate’s saved-name
expectations; two saved-header/navigation controls passed. Live read-only
validation then exposed an incorrect assumption in that initial candidate: a
restored name could override the saved ticket ID. That attempt was rolled back
with zero ticket writes. Two additional failing identity assertions reproduced
the issue locally, and the final repair preserves bootstrap identity on reload.
All six pass after the repair, including red sizes/colors,
SB extraction, direct edits, saved reload, Enter handling and print. All requests
use synthetic localhost fixtures; navigation destinations are intercepted.

Run with the loopback preview and a fresh Playwright CLI session:

```sh
playwright-cli -s=header-check open about:blank
playwright-cli -s=header-check --raw run-code --filename=scripts/header-checks.js
playwright-cli -s=header-check close
```

The JSON report must show `passed: 6`, `failed: 0`, and empty page-error and
external-request arrays. This extends the full frontend suite from 44 to 50
scenarios. Backend and real local API/PDF checks remain separate evidence.

## Verified publication

The corrected template from
[`4e5555194d9259672cddf122dc2f539acd6ae784`](https://github.com/krf1786/jobticket/commit/4e5555194d9259672cddf122dc2f539acd6ae784)
was published atomically at **2026-10-22 14:08:55 UTC**. Its SHA-256 is:

`326bbf9fd6a495ad842e761411842471c2bda31ee10cea358df8014a9e1511f2`

Public scratch and saved responses normalize to this exact source. All **21 live
browser checks** passed: both red numbers, scratch extraction/manual mirroring,
scratch Enter without saving or navigation, saved actual identity on reload,
explicit name edits, preserved material details/completion and print rendering.
The PDF generated locally from the live page shows both red numbers and the
completed/unchecked material marks; its rendered page was visually inspected.
There were no browser errors or blocked/unapproved requests.

Exactly four API writes targeted only the owned synthetic
`VERIFY-MATERIALS-20261021`. Its original state, including the blank Time field,
was restored exactly. `/jobticket/sb0000` was inspected read-only. The final server
audit at **14:13:49 UTC** confirmed all 13 pre-existing ticket rows unchanged,
unchanged backend hashes, and healthy service in the same process. Teams and the
production PDF renderer remain disabled. No Teams transport occurred.

The preceding code verification passed all **50 frontend scenarios, 17 backend
unit regressions and 40 isolated API/browser/PDF assertions**. Local Graph
transport was intercepted; these checks do not certify live SharePoint delivery.
[Sanitized release evidence](release-evidence.json) records the completed checks.

## Backup and rollback

Private original-template and integrity-checked SQLite backups, a release receipt
and a guarded rollback script remain on the server at:

`/root/jobticket/release-backups/header-20261022T140854Z/`

The replacement retained ownership and 0640 permissions. Only `ticket.html`
changed at runtime; no service restart, dependency/configuration change, or merge
was needed. The prepared rollback was not invoked for this corrected release:

```sh
python3 /root/jobticket/release-backups/header-20261022T140854Z/rollback.py
```

It requires the current template to match this release, atomically restores the
previous material-layout template (`39554748…`), and checks health. It never
restores the database. Verify both scratch and saved rendering after rollback.

The first candidate `7b1357a` was published at 01:00 UTC and rolled back when the
read-only saved-reference check exposed its identity error, before any API write.
It was never redeployed. The corrected release above supersedes that attempt.
Existing browser tabs must reload to receive the correction. PR #1 remains open
and unmerged; `main` remains unchanged.
