# Frontend release — October 22, 2026

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
