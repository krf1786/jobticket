# Backend release record — October 22, 2026

The backend safeguards from code commit
[`9d93b5976f0d7c8928fbb4014fd363a7039604b1`](https://github.com/krf1786/jobticket/commit/9d93b5976f0d7c8928fbb4014fd363a7039604b1)
were deployed successfully at 00:11:55 UTC. Only the running `app.py` was replaced,
followed by a verified service restart and healthy response. The frontend remains
an unreleased candidate, PR #1 is unmerged, and `main` is unchanged.

[Sanitized release evidence](release-evidence.json) records hashes, checks and
scope. Private execution receipts and database backups remain outside Git.
No credentials, private job contents, database-derived hashes or environment
files are published.

## Deployment and rollback evidence

Before replacement, the original module/template hashes matched the inspected
baseline and the approved test ticket was absent. Graph and the optional renderer
were disabled. A consistent SQLite backup passed `PRAGMA quick_check`; the
original app was also backed up. Both stay in the root-only server directory:

`/root/jobticket/release-backups/backend-20261022T001155Z/`

The repaired app was staged on the same filesystem, hash-verified, compiled with
production Python, and installed atomically with the existing root ownership and
0640 mode. `jobticket.service` restarted into a different process and returned
healthy. The live template, `graph.py`, `pdf.py`, service/proxy configuration,
credentials and dependencies were not changed. Aggregate before/after checks
confirmed every pre-existing ticket row was unchanged.

Atomic app replacement, restart, original-file rollback and restart were rehearsed
against an isolated local service and synthetic SQLite state. The live fallback
was prepared but was **not invoked**, because deployment succeeded. The saved
server-side rollback script is:

```sh
sh /root/jobticket/release-backups/backend-20261022T001155Z/rollback.sh
```

It restores only the original app, preserves its ownership/mode, and restarts
`jobticket.service`. After invoking it, verify service health and the original
app hash in [backend-source-manifest.json](backend-source-manifest.json). Do not
restore the database automatically over newer user writes. Rolling the backend
back would also remove the new legacy-client protections.

## Authorized live persistence test

At 00:13:11 UTC, the public API was checked again and returned 404 for
`VERIFY-MATERIALS-20261021`. An INSERT-only reservation prevented overwriting an
unexpected concurrent creation. Subsequent tests used real public API PUT/GET
requests and the saved-page bootstrap, solely for that clearly synthetic ticket.
The test finished at 00:13:12 UTC with **14 checks passing**:

- Details and completion survive saving, API reload and server bootstrap.
- Old payloads omitting either additive field preserve it when rows are unchanged.
- Ambiguous old-client row changes return 409 without any write.
- Updated payloads deliberately clear/uncheck, delete aligned rows and reset.
- The synthetic ticket remains clearly labeled; it was not permanently deleted.
- All pre-existing ticket rows remain unchanged; the live frontend/Graph/PDF
  module hashes are unchanged; service health remains good.
- Teams and renderer remain disabled and the synthetic ticket has no push record.

There were zero Teams transport calls, uploads, existing-job edits, credential
changes or integration installations. The still-old live frontend does not expose
the new controls; live persistence was verified through the API and its bootstrap,
while candidate browser interactions were verified locally.

## Local verification and review limits

The tested code passed 44 frontend scenarios, 17 backend regression methods and
40 isolated integration assertions. The latter exercise real API, SQLite,
browser autosave/restoration and PDF rendering; external Graph transport is
intercepted. All 180 long-detail lines survive a four-page PDF, and checked versus
unchecked print marks remain distinguishable without relying on green color.
Relevant regressions failed before their fixes. See [backend-fixes.md](backend-fixes.md),
[material-details.md](material-details.md) and [verification.md](verification.md).

The latest fetched GitHub review still targets original capture commit `57f8f6b`.
Its three findings were fixed in `6ef71bb` and remain covered by passing tests.
GitHub marks those threads outdated but unresolved; no fresh review of the repaired
code was returned. Zero check runs were reported for code commit `9d93b59`.
These facts are not a new review approval or a CI pass.

## Remaining release action

The layout can be published only after separate approval. Back up the current
live `ticket.html`, recheck its baseline hash and backend health, then atomically
replace it with the verified `frontend/ticket.html`. The template is read per
request, so no backend restart is needed. Verify scratch and synthetic saved
rendering; restore the original template on failure. This template swap/rollback
was tested locally without changing stored state. Existing tabs should reload to
use the new controls; legacy row conflicts intentionally show the old save-error
state until they reload.

Git push or PR merge is not the deployment mechanism. Teams remains unavailable
because production Graph configuration and optional PDF dependencies are absent.
Their setup and real SharePoint delivery require separate work and authorization.
No production Teams/PDF delivery success is claimed by this release record.
