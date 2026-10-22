# Compact material rows and Return-key release

Single-line Material / Material details rows now match Production Steps at 21px
instead of 34px, with a smaller 16px completion checkbox. Details start at one
line and still grow/shrink for wrapped or multiline text. Mobile text retains its
12px size with compact line spacing. Enter in Material details adds the next
numbered row and focuses its Material field, matching the existing Material
input behavior. Shift+Enter inserts a newline in details. Production instructions
retain ordinary Enter newlines.

## Publication and verification

Source commit [`1181e42a2c9317504bb5aa7c517186c0e0521b30`](https://github.com/krf1786/jobticket/commit/1181e42a2c9317504bb5aa7c517186c0e0521b30)
was published at **2026-10-22 14:57:40 UTC** by atomic replacement of only
`/root/jobticket/ticket.html`. The new template SHA-256 is:

`618aa4ea8709aaa286ab6be690148cc069cc17f90bdb77a08f8eb5df64004958`

The current template and all backend hashes matched the previous corrected
release before publication. Public scratch and designated saved synthetic pages
normalize to the new template. Backend sources, configuration, dependencies and
credentials are unchanged, with no restart. All 14 ticket rows were unchanged
during publication.

Fresh local checks passed all **51 frontend scenarios** and 9 focused browser
checks, with no JavaScript errors or external requests. Source hashes, three
inline script syntax checks, bootstrap safety and preview API rejection passed.
Screen and print screenshots were inspected. The existing backend unit and
integration totals remain historical evidence; this change touches no backend.

All **24 live checks** passed, including 21px row heights at 1200px, 390px and
320px; checked and unchecked states; Enter from both Material and details; focus
and text preservation; Shift+Enter; detail growth/shrink; saved row persistence,
reload, aligned completion; actual saved header identity; and print mirrors.
Scratch tests sent no API writes. Exactly three writes targeted only
`VERIFY-MATERIALS-20261021`, including its exact-state cleanup. Its state was
restored exactly. The final server audit at **15:00:11 UTC** confirmed all 13
other ticket rows unchanged, unchanged backend hashes, the same service process,
and healthy service. There were no browser errors or unapproved requests.

Teams and the production PDF renderer remain disabled. No transport, installation
or credential change occurred. Print verification does not establish production
SharePoint/PDF delivery. PR #1 remains open and unmerged; Git push/merge is not
the deployment mechanism. See [sanitized evidence](release-evidence.json).

## Backup and rollback

The previous corrected template and an integrity-checked SQLite backup are in:

`/root/jobticket/release-backups/material-rows-20261022T145740Z/`

The replacement preserves the existing ownership and permissions. The prepared
rollback was not invoked:

```sh
python3 /root/jobticket/release-backups/material-rows-20261022T145740Z/rollback.py
```

It refuses to overwrite a later template, atomically restores the previous
corrected header/material template (`326bbf9f…`), and checks health. It does not
restore the database or restart the service. Recheck scratch and saved rendering
after rollback.
