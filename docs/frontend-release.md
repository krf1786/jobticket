# Frontend release — October 22, 2026

This records the initial material-layout publication. The subsequent
[verified header correction](header-fix.md#verified-publication) is the current
live template; the hash and rollback below refer to this earlier release.

The approved layout is live at <https://graphlab.info/jobticket/>. Only the
runtime `ticket.html` was replaced, atomically, at **00:36:55 UTC**. The source
was PR head [`ee356916517260605149d81b4578d48ee3f1023d`](https://github.com/krf1786/jobticket/commit/ee356916517260605149d81b4578d48ee3f1023d),
whose template is byte-identical to the tested code commit `9d93b59`.

Deployed template SHA-256:

`395547481472968e3925a065bc191e09f276df3f298efe9f1c2fd91427231481`

Both public scratch and existing synthetic saved pages normalized to this exact
template hash. The service remained healthy in the same process; no restart,
backend/module change, asset replacement, credential/dependency installation,
Teams configuration or PR merge occurred. `main` remains unchanged.

## Preconditions and backup

The live template, repaired backend and font hashes matched their verified
versions. The test ticket matched its recorded creation time and prior synthetic
state, so no unexpected source or ticket changes were overwritten. The current
backend/template swap and rollback were also rehearsed locally with synthetic
SQLite state before publication.

The original template and a consistent SQLite backup remain in this root-only
server directory:

`/root/jobticket/release-backups/frontend-20261022T003654Z/`

The database backup passed its integrity check. The staged template retained root
ownership and 0640 permissions. Original template SHA-256:

`bf0ad0ab27a84ce2d6b69f805e950f49d47f262b14d0808ec19b3d429cc11af1`

Rollback was prepared but not invoked. If required, the saved procedure is:

```sh
python3 /root/jobticket/release-backups/frontend-20261022T003654Z/rollback.py
```

It refuses to overwrite a template that changed since this release, restores the
original template atomically with its ownership/mode, and checks health. No
restart or database restore occurs. Check both saved and scratch rendering after
rollback. The repaired backend protections remain installed.

## Live verification

The existing, clearly synthetic `VERIFY-MATERIALS-20261021` was the only writable
ticket. Browser request routing allowed public scratch/static reads and that
specific ticket's GET/PUT requests; all other requests were blocked by default.
The passing run attempted no unapproved requests and had no JavaScript errors.
All **19 live browser checks** passed, including:

- Scratch details/checkbox edits remain unsaved and send no API requests.
- Saved details and completion restore from the live bootstrap.
- Detail edits autosave and survive reload; completion check/uncheck both
  persist, with the whole-row light green highlight correctly added/removed.
- The narrower material column, larger details area and far-right checkbox
  remain usable at 1200px, 390px and 320px widths.
- Print shows full multiline details and explicit checked/unchecked marks.
  A PDF generated locally from the live page contains those details and marks;
  this does not use or install a production PDF renderer.
- Synthetic state is restored after testing; its final notes then identify the
  completed release verification. Every other ticket row remains unchanged.

Screen and print screenshots were reviewed. The long synthetic identifier still
exceeds the original fixed-width job-number input; this inherited header behavior
was not changed by the material-layout release. Normal short job numbers remain
covered by the local baseline regression suite.

The first run passed feature/layout/print checks but its final exact-state cleanup
assertion found the original form's automatic Time-field default. Comparison with
the immutable capture confirmed this was existing behavior. Only that owned
synthetic fixture field was restored, cleanup was corrected to clear it, and all
19 checks were rerun successfully. No application code change or rollback was
needed for this test-fixture issue.

Final server audit at **00:41:01 UTC** confirmed healthy service, unchanged backend
hashes and unchanged pre-existing ticket rows. The synthetic ticket is retained
and clearly labeled. Private receipts, database backups and job state stay outside
Git; [sanitized evidence](release-evidence.json) records the release facts.

## Limits

Teams remains disabled. No Graph credentials or renderer dependencies were added,
and no Teams/SharePoint transport or image upload occurred. Real production
Teams/PDF delivery remains unverified. Existing browser tabs should reload to
receive the new layout; older-tab row conflicts are protected by the backend.
PR #1 remains open and unmerged; publication used the authorized template swap.

## Reset button removal

The toolbar Reset button was removed in `fabb5a13f5116d444786f5f9d590d0cd8f953530`.
Only that button markup changed in the runtime frontend; all JavaScript remains
identical. Existing legacy reset regression cases now call the retained helper
directly. All 57 frontend scenarios, source/syntax/bootstrap/preview checks and
nine focused toolbar checks passed locally. The isolated backend verification
script's legacy reset calls were updated but that integration suite was not rerun.

Published atomically at **2026-10-23 02:08:17 UTC** (October 22 locally). Template
SHA-256: `c691d89d053c79b26284b36914061e917764a8c81acc04a4844ba1da1c1dd304`.
The same nine focused checks passed live: Reset is absent at desktop/mobile
widths, Print and Check Due remain, Print still invokes printing and the toolbar
is hidden in print. Screenshots were inspected. No API writes or browser errors
occurred; all 16 saved rows were unchanged at the final audit. Backend sources
and service process are unchanged. PR #2 remains unmerged.

The previous template, integrity-checked SQLite backup and guarded rollback are
in `/root/jobticket/release-backups/reset-button-20261023T020817Z/`. Rollback,
not invoked: `python3 /root/jobticket/release-backups/reset-button-20261023T020817Z/rollback.py`.
It refuses to overwrite a newer template and restores only the previous template,
without restoring data or restarting the service. Production PDF/Teams delivery
remains disabled and unverified.

## Check Due button removal

Only the Check Due toolbar button was removed in
`25f7c47c919e3feaf8e4744c6ac78651511076f8`. Print remains; all JavaScript and
the Due Date field's change handler remain unchanged. Source hashes, syntax,
bootstrap and preview safety checks passed. Nine local and nine live toolbar
checks passed at 1200/390/320px, including Print activation and print visibility,
with no API writes or browser errors. Toolbar screenshots were inspected.

Published atomically at **2026-10-23 02:57:11 UTC** (October 22 locally), SHA-256
`a572d7740587098dbe4850f59adc1c24d0fc65f0ead1fc3a05d6c7b69f019f97`.
All 16 ticket rows were unchanged at the final audit. Backend and service
process are unchanged. PR #2 remains unmerged; production PDF/Teams delivery
remains disabled and unverified. Backup and guarded rollback are in
`/root/jobticket/release-backups/check-due-button-20261023T025711Z/`. To roll back,
run its `rollback.py`; it refuses to overwrite a newer template and restores
only the previous template, without data restore or service restart. Rollback
was not invoked.
