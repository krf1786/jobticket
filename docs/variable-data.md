# Variable Data flag

The Job Information heading has a blank 16px checkbox immediately to its right.
Checking it reveals **Variable Data** in bold green text to the right of the box;
unchecking it hides the text. Its accessible name remains Variable Data in both
states. Keyboard Space toggles the native checkbox, and print retains its state
and the conditional label.

Saved tickets persist the boolean `variableData` through the existing serialized
autosave. Historical tickets with no field display unchecked; scratch tickets
remain unsaved. A legacy tab that omits the field preserves the prior saved
value. Explicit `false` unchecks it, and supplied non-booleans are rejected with
HTTP 400 before writing. The retained reset helper clears it only after reset
confirmation. No existing ticket records are backfilled or migrated.

This change touches only the ticket template and the app's state handling. It
does not change corkboard source, sticky notes, material rows, attachments,
images, authentication, Graph or production PDF delivery.

## Verification

Three new backend regression methods cover legacy omission, explicit unchecking,
and invalid values without writes. All 43 backend/storage regression methods
pass. All 24 focused checks in `scripts/variable-data-checks.py` pass against a
disposable real API/SQLite service, with no external requests or browser errors.
They cover exact true/false autosave and reload, old-tab omission, invalid values,
scratch behavior, keyboard activation, placement at 1200/390/320px, preserved
adjacent data/attachment bytes/corkboard state, and both printed states. Desktop,
mobile and rasterized Letter PDFs were visually inspected. The 45 existing
browser/save/material scenarios and source/syntax/preview checks also pass.
Generated evidence stays under ignored `output/variable-data/`.

Publication and live verification are recorded separately in
`docs/variable-data-release.md` once completed. A Git commit or PR is not a
production deployment.
