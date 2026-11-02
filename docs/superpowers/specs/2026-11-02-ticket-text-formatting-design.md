# Job Ticket text formatting

Status: approved by Kyle on November 2, 2026, with the additional material QTY
column below. Kyle requested three highlighter colors, bold, font size,
text color and additional formatting, and chose all text fields including job
names and material names. This proposal is for the Job Ticket editor.

## Experience and scope

Add one compact toolbar for the focused text field: **bold**, italic, underline,
font size, text color, yellow/pink/green highlighting, and Clear Formatting.
Formatting applies to selected words; with a collapsed selection it applies to
newly typed text. The toolbar reflects the current selection and keeps it when
a formatting control is used. Undo/redo must preserve both text and formatting.

Support job names, material names, material details, production operations,
production instructions and Notes. Material names and job names remain single
line. Multiline details, instructions and Notes retain line breaks and wrapping.
The job number remains a routing identifier with its current red mirrored
display; date, due date, time and quantity retain native structured controls.
These identifier/structured fields are not prose-formatting targets.

Keep existing styling as the default on tickets with no formatting. Choosing a
larger font may increase a row's height; unformatted one-line material rows must
retain the current compact height. Text color is user-selectable; Clear
Formatting restores the field's original size/color/weight. The three highlight
colors are pale enough to keep text readable. Material completion still colors
the row light green independently of highlights.

Keep the same material suggestions available through an accessible picker.
Material/Details Enter still adds the next material row; Shift+Enter inserts a
details line break. Production operation Enter still adds a row and instruction
Enter remains a line break. Job-name job-number extraction/navigation and the
Variable Data checkbox continue working. Copy/paste must work without importing
uncontrolled markup or outside styles; plain-text paste is the safe default.

Formatted text saves automatically with the ticket and restores after reload.
Scratch tickets stay unsaved. Formatting appears in browser print and the
corkboard's existing visual ticket preview; formatting controls do not print.
Check desktop and touch/narrow-screen selection/tool use.

## Approach

Use directly editable rich text fields with a shared toolbar. Preserve the
existing exact plain strings in the ticket's current fields, and store a
versioned, bounded sidecar of structured text runs/marks. Render using text nodes
and approved span styles, not arbitrary saved HTML. This keeps routing, material
names and integrations based on their existing plain values.

Native input/textarea controls cannot display mixed formatting. Whole-field
styling would not support highlighting selected words. A separate modal editor
would make normal typing and material selection less direct. Transparent input
overlays would misalign selection/carets with mixed font sizes. The proposed
inline editors are the practical way to meet the selected-text request.

Bind formatting to exact text and stable row identity; use existing material IDs
and stable production-row IDs. Add/delete/reorder must keep styles with their
own text, including duplicate row values. Save plain text and matching marks in
one serialized request. Backend validation rejects inconsistent runs, unknown
styles, invalid colors/sizes and excessive data before writing.

Older tabs omitting formatting preserve it when their associated text/row
identity is unchanged. If an older tab changes formatted text or ambiguously
changes rows, reject that save with a reload message rather than silently
discarding formatting. New clients can deliberately remove formatting. Existing
material-file baselines and Variable Data omission protection remain in force.

Implementation may adapt the existing controls through shared editor helpers;
do not maintain two conflicting visible editing surfaces. Prefer a small local
implementation with no new production Python dependencies. If an editor library
becomes necessary, choose and document it before implementation; do not add a
runtime CDN dependency or external data service.

## Boundaries and verification

Add a narrow **QTY** column between Material and Material Details, wide enough
for two digits. Each row starts blank and accepts a nonnegative whole-number
quantity. Column width is a layout choice, not a two-digit maximum. Quantities
save/reload, remain aligned through row addition/deletion/reset and print. Older
tabs must not silently erase meaningful quantities or guess their row mapping.

Preserve all ticket fields, images, 100 MB attachments, material completion,
saved job identity, date defaults, serialized saves and toolbar removals. No
corkboard editing feature, sticky-note implementation, access change, Graph/
Teams setup or production PDF dependency installation is included.

Use isolated SQLite/API/browser fixtures for formatting, literal hostile paste,
mixed selections, toolbar focus, undo/redo, explicit Clear Formatting, reload,
autosave failure/races, duplicate rows, row changes, material suggestions,
keyboard shortcuts, touch/mobile, print and visual preview checks. Keep relevant
existing regression coverage. Check printed colors and complete long text on
rasterized PDFs; do not infer production PDF delivery from local printing.

Before publication, inspect current live sources and configuration, back up both
databases and changed code, prepare guarded code-only rollback, and deploy the
exact verified commit. Live write tests may use only the labeled
VERIFY-MATERIALS-20261021 ticket, followed by guarded exact restoration including
its timestamps. Preserve all customer tickets and shared-board data. No PR
merge is automatic. Report implementation, local tests and live verification
separately.
