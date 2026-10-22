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
but missed scratch header interaction. Saved headers intentionally start from the actual bootstrap job ID; a stored
job name can mention a different SB number and must not silently replace it.

## Scoped repair

Header initialization now runs independently of persistence. Scratch mode binds
job-name extraction and manual-number mirroring but remains unsaved: typing or
pressing Enter there does not save or create a ticket. The empty left placeholder
uses the existing red color; the right number appears when a real number is entered.
No placeholder is treated as an actual ticket identity.

Saved mode initializes both numbers from the actual bootstrap job ID after
reload, even when the restored name mentions another number. Typing a name containing `SB4321`, `SB 4321` or `SB-4321` fills both corners in uppercase. Direct
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
the issue locally, and the final repair preserves bootstrap identity on reload. All six pass after the repair, including red sizes/colors,
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

The first attempt at 01:00 UTC was rolled back after the saved-reference check;
no API writes had occurred. Final live publication and verification are recorded in the release evidence after
completion. No production reference-ticket edits or Teams transport are used.
