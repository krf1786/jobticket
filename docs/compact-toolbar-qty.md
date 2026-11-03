# Compact toolbar and material quantity controls

Print and Saved share the first toolbar row; formatting sits immediately below.
At1200px the toolbar measures79px, down from131.5px, without removing controls.
The layout wraps on phones. Print and image exports still hide editing controls.

Materials now start with QTY, followed by Material and Material Details. QTY has
visible up/down buttons and keyboard ArrowUp/ArrowDown support. Step size is one;
blank increases to1 or decreases to0, values never go below0 or above999999999,
and unchanged boundary clicks do not schedule saves. The existing integer
validation and feedback stay in force. Changing a quantity uses the same input/
autosave path as typing, so row alignment, formatting, completion and attachment
state are preserved. Added/deleted rows receive correctly numbered labels.

The column is48px on desktop/print and44px on narrow phones, leaving room for two
digits and buttons. Empty desktop material rows remain21px high. The small-phone
Done heading stays readable, and Details retain at least60px usable text width.
Print includes the quantity once, without the editing buttons. There are no
backend, schema, dependency or configuration changes.

Verification uses scripts/compact-qty-checks.py with a disposable real API/SQLite
backend and original-byte attachment fixture. Rendered desktop/mobile/print
artifacts stay in ignored output/compact-qty/. Publication and live verification
are recorded separately in compact-toolbar-qty-release.md.
