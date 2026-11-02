# Ticket formatting and per-material QTY

All prose fields use inline rich editing: job name, material name/details,
production operation/instructions and Notes. The shared toolbar applies bold,
italic, underline, font size, text color and yellow/pink/green highlighting to
selected text or newly typed text. Clear Formatting restores original styling.
Undo/redo and Ctrl/Cmd+B/I/U work in the active field. Job numbers, date/time,
job quantity and material quantities retain ordinary structured controls.

Material suggestions remain available using the arrow beside the name. Material
name/details Enter adds a row; details Shift+Enter adds a line. Production
operation Enter adds a row; instruction and Notes Enter insert a line. The QTY
column is narrow enough for two digits but accepts larger nonnegative whole
numbers (up to nine digits). It starts blank and prints with its material.

Defaults preserve the compact desktop layout. Larger chosen fonts can increase
row height. Highlights use dark text unless an explicit text color was selected,
including in the originally white job name. Formatting and quantities autosave
and reload with saved tickets; scratch tickets remain unsaved. Print and the
existing corkboard visual preview render formatted text without the toolbar.

## Data contract

Existing plain fields remain exact strings. The sidecar is
`richText: {version: 1, fields: {fieldKey: runs}}`. Each run contains literal
`text` and optional `bold`, `italic`, `underline` booleans, integer `size` (8–48
CSS pixels), six-digit hex `color`, and `highlight` from `#fef08a`, `#fbcfe8` or
`#bbf7d0`. Concatenated run text must exactly equal its associated plain field.
No arbitrary saved HTML, external style, image, link or script is rendered.

Keys are `jobName`, `notes`, `material:ROW_ID:name`,
`material:ROW_ID:details`, `production:ROW_ID:op` and
`production:ROW_ID:instr`. Existing material row IDs are reused;
`productionRowIds` is a stable array aligned with steps.
`materialQuantities` contains aligned blank/integer strings. Duplicate rows keep
their own values and styles through deletion/reordering.

`richTextBase` is request-only, recording the last acknowledged complete sidecar.
It is removed before storage. A stale baseline returns409 before writing, and
acknowledgement uses the sent snapshot rather than newer unsaved changes.
Explicit empty fields clear formatting. Older tabs omitting metadata preserve
it only when exact associated text and identity remain safe; ambiguous edits to
formatted text/quantity-bearing rows return409 and require reload.

Invalid runs, colors, sizes, quantities and row IDs return400 without writing.
Existing material-file baselines, Variable Data preservation and save queue
behavior remain in force. No existing records are automatically migrated.

## Verification and release

`tests/test_rich_text.py` covers validation and legacy/concurrent saves.
`scripts/rich-editor-checks.js` tests the editor independently.
`scripts/formatting-checks.py` exercises the disposable real API/SQLite/browser
workflow, print and visual-preview export. Evidence stays in ignored output/.
Publication and live checks are recorded separately after release. The live
corkboard backend is newer than this branch's historical capture and must be
preserved during the ticket-only release. Production Graph/PDF/Teams delivery
remains disabled and unverified.
