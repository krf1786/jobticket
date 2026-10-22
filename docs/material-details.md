# Material details columns

This user-requested branch change follows the original capture (`57f8f6b`) and
the save/reset/Teams fixes (`6ef71bb`). It is not part of the captured live baseline
and has not been deployed.

Each row in Materials / Components now divides its editable area equally:
the existing Description dropdown on the left and a separate **Material details**
column on the right. The row number, delete button, and reference image remain.
Details wrap and grow with their content; Enter adds a newline there, while
Enter in the material dropdown still adds a row. Print uses plain-text mirrors
for both values so long content wraps without an input or textarea clipping it.
User text is assigned with `textContent`, including literal HTML-like text.

Below 600px, the reference image moves under the table, the job information
uses two columns, and the page fits the viewport instead of scaling a fixed
letter-size sheet. The two material columns remain side by side. Desktop and
print retain the existing letter-size page and reference-image placement.

## State and compatibility

The original `materials: string[]` contract remains intact. A parallel
`materialDetails: string[]` records each row's details at the same index:

```json
{
  "materials": ["Clear acrylic", "White acrylic"],
  "materialDetails": ["Cut to 12 × 24 in\nPolish edges", "3 mm, matte finish"]
}
```

Both arrays are collected from the same ordered DOM rows. Deletion keeps them
aligned. Missing details restore as blank, so existing tickets need no client
migration. Cancelled Reset changes nothing and issues no save; confirmed Reset
produces one blank material and one blank detail. Scratch mode remains unsaved.
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
state and mocked local API responses. All six scenarios failed before the
field existed; all six pass after this change, with no page errors or external
requests. Coverage includes:

- Legacy tickets without details and equal-width adjacent columns.
- Multiline entry, newline versus add-row behavior, PUT serialization, reload
  restoration, and aligned row deletion/accessibility labels.
- Cancelled and confirmed Reset.
- A held save response preventing Teams push until details are saved.
- 320px and 390px layouts, textarea growth, literal-text print wrapping, and a
  locally generated print PDF.
- Scratch editing without API writes.

With the loopback preview running, use a fresh Playwright CLI session:

```sh
playwright-cli -s=material-details open about:blank
playwright-cli -s=material-details --raw run-code \
  --filename=scripts/material-details-checks.js
playwright-cli -s=material-details close
```

The JSON result must report `passed: 6`, `failed: 0`, and empty `pageErrors`
and `externalRequests`. Check that result, not only the CLI exit code.
Screenshots and PDF are synthetic, under ignored `output/playwright/`.
