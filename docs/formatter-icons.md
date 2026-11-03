# Formatter icons

The formatting toolbar uses familiar B/I/U glyphs, an A with a current-color
underline, three colored highlighter symbols and a T/eraser Clear Formatting
icon. Font size stays numeric, initially10; mixed sizes use the compact ↕
placeholder. All existing actions retain their exact accessible names and native
hover tooltips. Decorative spans/SVGs are hidden from assistive technology.

The native color input remains the actual pointer/keyboard target, with a
visible focus ring around its A wrapper. The underline follows the selected
text's color as well as new color choices. Selection preservation, formatting
commands, keyboard shortcuts, persistence and data schema remain unchanged.

The desktop toolbar now fits on one45px row with Print/Saved; phone controls
wrap below Print/Saved. At390/320px the toolbar measures79/111px. No controls are
removed. Print and the existing SVG ticket preview hide all editing controls.
The QTY position/buttons and compact material rows remain intact.

Verification: scripts/formatter-icon-checks.py exercises a disposable real
backend and browser, including icon/accessibility/tooltip coverage, color input
pointer/focus, all actions, selection, zero initial saves, responsive layout,
print and actual SVG export. The existing editor fixture and50 formatting
integration checks also pass. Artifacts stay in ignored output/formatter-icons/.
No backend/dependency/configuration changes or live ticket write tests are
needed for this presentation-only update; publication is recorded separately.
