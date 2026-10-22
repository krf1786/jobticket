# Today date autofill

Blank Date fields now use the browser's local calendar date, including after
confirmed Reset. Nonempty saved dates are preserved. Cancelled Reset keeps the
chosen date. The default is included in the next normal save without saving on
initial load. Reset recomputes today if the page has remained open past midnight.

The prior initializer used UTC (`toISOString`) and Reset left Date empty. The
shared initializer now uses local calendar getters; no backend behavior changed.

Source commit [`82fec39d2b9041c2ac5af581d671ddc44eb014fc`](https://github.com/krf1786/jobticket/commit/82fec39d2b9041c2ac5af581d671ddc44eb014fc)
passed all **57 local frontend scenarios**, including six date cases. Four date
cases reproduced the defects before repair. Hash/syntax/bootstrap/preview checks
passed. The template was published atomically at **2026-10-22 15:39:12 UTC**.
Its SHA-256 is:

`28dd824bb9b5a3058d3b05898fa87b7485bb683dad12f2b4c9918b5cbe42b016`

Public scratch and designated saved responses match the new source. All **nine
live checks** passed: today's local default, confirmed/cancelled scratch Reset,
saved-date load/reload preservation, New York and Tokyo across UTC midnight,
unchanged saved state, and no JavaScript errors or unapproved requests. The
rendered live Date field was inspected. All live checks were read-only, with
zero API writes. The final server audit at **15:39:43 UTC** confirmed all 14
ticket rows unchanged, unchanged backend hashes, healthy service, and no restart.

The previous template and integrity-checked SQLite backup remain in:

`/root/jobticket/release-backups/date-autofill-20261022T153912Z/`

The prepared, unused rollback is:

```sh
python3 /root/jobticket/release-backups/date-autofill-20261022T153912Z/rollback.py
```

It guards against later template changes and restores only the previous template,
without a database restore or restart. Check scratch and saved rendering afterward.
PR #1 remains open and unmerged. Teams and production PDF delivery remain disabled
and unverified. See [sanitized release evidence](release-evidence.json).
