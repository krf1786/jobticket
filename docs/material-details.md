# Material details columns

This user-requested branch change follows the original capture (`57f8f6b`) and
the save/reset/Teams fixes (`6ef71bb`). It is not part of the captured live baseline
and was published with completion controls on October 22, 2026. See the
[frontend release record](frontend-release.md) for the exact source/hash and live checks.

Each row in Materials / Components now uses about 28% of its editable width
for the Material dropdown and the rest for **Material details**. A compact
Completed checkbox sits at the far right, after the delete control. The main
job description bar, row number and reference image remain. This narrower split
and completion control supersede the original equal-width layout.
Single-line rows match the height of Production Steps, with a smaller 16px
completion checkbox. Details wrap and grow with their content. Enter in either
Material or Material details adds the next numbered row and focuses its Material
field; Shift+Enter in details inserts a newline. Production instructions retain
their existing Enter-for-newline behavior. Print uses plain-text mirrors
for both values so long content wraps without an input or textarea clipping it.
User text is assigned with `textContent`, including literal HTML-like text.

The reference-image box spans the full ticket width below Notes: 320px tall on
desktop and 240px below 600px. Images retain their proportions without cropping.
Materials now use the full available width. Below 600px, job information uses two
columns and the page fits the viewport; the material columns remain side by side.
Print retains the Letter page and keeps the reference-image box together.

## State and compatibility

The original `materials: string[]` contract remains intact. A parallel
`materialDetails: string[]` records each row's details at the same index:

```json
{
  "materials": ["Clear acrylic", "White acrylic"],
  "materialDetails": ["Cut to 12 × 24 in\nPolish edges", "3 mm, matte finish"],
  "materialCompleted": [true, false]
}
```

`materialCompleted: boolean[]` uses the same row index. All three arrays are
collected from the same ordered DOM rows. Only literal `true` restores as checked;
missing or invalid completion values default to unchecked. Checked rows have
a very light green (`#f0fdf4`) background across every cell. Unchecking restores
the normal background. The accessible label is Completed plus the row number.
Print shows explicit `[x]`/`[ ]` marks as well as the highlight, so color is not
the only completion indicator. Deletion keeps them
aligned. Missing details restore as blank, so existing tickets need no client
migration. Cancelled Reset changes nothing and issues no save; confirmed Reset
produces one blank material, one blank detail and an unchecked completion flag. Scratch mode remains unsaved.
The existing revision-aware save queue handles detail edits and completes their
PUT before the explicit Teams push.

The deployed backend source was subsequently obtained and matched the local
installer modules byte for byte. Its real SQLite/API and PDF rendering paths
were tested in isolation with the candidate template. The backend stores details
and the existing PDF renderer includes them, including long wrapped content.
[Backend repairs](backend-fixes.md) now preserve omitted details from older tabs
and reject ambiguous old-client row changes with HTTP 409. Explicit updated
payloads can still clear, reset or delete rows.

Live persistence evidence and remaining Teams limitations are recorded in
[the release record](backend-release.md). Local intercepted Graph tests are
not proof of production Teams delivery.

## Local regression evidence

`scripts/material-details-checks.js` executes the real template with synthetic
state and mocked local API responses. The original six scenarios failed before the
details field existed and passed after it was added. The current eleven scenarios
also cover the narrower layout and completion controls, with no page errors or external
requests. Coverage includes:

- Legacy tickets without details/completion and the narrower material column.
- Multiline entry, newline versus add-row behavior, PUT serialization, reload
  restoration, and aligned row deletion/accessibility labels.
- Cancelled and confirmed Reset.
- A held save response preventing Teams push until details are saved.
- 320px and 390px layouts, textarea growth, literal-text print wrapping, and a
  locally generated print PDF.
- Scratch editing without API writes.
- Compact row heights matching Production Steps at desktop, 390px and 320px;
  completion toggling and growth/shrink after wrapping.

With the loopback preview running, use a fresh Playwright CLI session:

```sh
playwright-cli -s=material-details open about:blank
playwright-cli -s=material-details --raw run-code \
  --filename=scripts/material-details-checks.js
playwright-cli -s=material-details close
```

The JSON result must report `passed: 11`, `failed: 0`, and empty `pageErrors`
and `externalRequests`. Check that result, not only the CLI exit code.
Screenshots and PDF are synthetic, under ignored `output/playwright/`.

The completion follow-up first failed six browser scenarios (two width checks
and four completion cases) against the prior template, with four compatibility
controls passing. After implementation all ten pass. Coverage includes toggle,
whole-row highlight, serialization/reload, row addition/deletion, cancel/confirm
Reset, old-ticket defaults, 320px/390px alignment, scratch mode and print marks.

The [compact-row and Return follow-up](material-row-release.md) records the latest
verified live template, test scope and guarded rollback.
