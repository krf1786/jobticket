# Backend release record

Status before production action: the backend repairs are tested locally; the
frontend remains an unreleased candidate. The authorized production scope is
only replacement of the backend `app.py`, a graceful service restart, and
persistence checks on `VERIFY-MATERIALS-20261021` after confirming it is absent.
No existing job may be edited. No template, Graph configuration, dependencies,
proxy configuration, Teams transport or PR merge is authorized by this repair.

## Procedure

1. Recheck original hashes, service health, absent test ticket, disabled Graph
   and absent renderer. Stop if preconditions changed.
2. Make a root-only timestamped backup of `app.py` and a consistent SQLite
   backup on the server. Record an aggregate digest of existing rows without
   exporting their contents. Stage only the repaired app beside the original,
   preserve ownership/mode, verify its hash and compile with production Python.
3. Atomically replace `app.py`, then restart `jobticket.service`. Check bounded
   health readiness and unchanged template/Graph/PDF hashes. On failure restore
   the original app atomically, restart and verify health. Do not restore the
   database automatically over newer user writes.
4. Recheck the dedicated test ticket is absent and reserve it using INSERT-only
   semantics so an unexpected existing row cannot be overwritten. Use real API
   PUT/GET for synthetic material-details persistence, omitted-field protection,
   conflict rejection and explicit clearing. Leave the ticket clearly labeled.
5. Verify health, unchanged existing-row digest, unchanged template and disabled
   Teams. Record actual results and backup location after execution.

Frontend release requires a separate authorized atomic replacement of the live
`ticket.html` with the verified `frontend/ticket.html`; it is read per request,
so no backend restart is needed. Back up the original template first, verify
health and both saved/scratch rendering, and restore that file on failure.
Git push/merge is not the deployment mechanism. Graph credentials/renderer setup
and real Teams delivery remain separate unresolved integration work.
