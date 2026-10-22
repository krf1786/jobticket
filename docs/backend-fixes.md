# Backend repairs after source capture

The deployed backend was first preserved byte for byte in commit
`bdc201b2ca30085a4973eba48cfbc728b624cf65`. These are subsequent repairs, not
claims about the captured baseline. Only `backend/app.py` changes behavior;
`graph.py` and `pdf.py` remain identical to the deployed sources.

## Older tabs and material details

Whole-state saves from older editors omit `materialDetails`. For an existing
ticket with that field, omission preserves details when `materials` is unchanged.
If an old editor changes material rows while nonempty details exist, the entire
save is rejected with HTTP 409 and a reload instruction. Matching by material
name would be unsafe for duplicate names, renaming, reordering and deletion.
The old UI shows its existing save-error state; users need to reload the updated
editor before changing protected rows. No unrelated fields are partially saved.

An explicit `materialDetails` field remains authoritative. The updated editor
can deliberately clear details, delete rows or reset the form. Old tickets that
never had details keep their original behavior. Old editors can change rows
whose existing details are all blank; the stored blank array is realigned.
This is additive-field protection, not general multi-editor conflict resolution.

## PDF revision and upload ordering

A push captures `updated_at` before rendering and acknowledges that revision
only after a successful upload. A newer save during rendering/upload remains
stale and eligible for the next push. The old implementation used completion
time and could incorrectly mark that newer save synchronized.

A process lock now spans rendering and upload, so an older in-flight upload
cannot overwrite a newer PDF after it completes. The verified deployment uses
one uvicorn process. This lock is not distributed and must be revisited before
adding multiple service workers. `updated_at` is strictly increasing even when
two saves share a clock tick or the clock steps backwards.

The renderer can observe a newer save than the pre-render revision; acknowledging
only the captured revision is deliberately conservative and queues another push.
`pushedAt` now identifies the acknowledged saved revision, not upload wall time.
The change does not freeze other clients or add a general snapshot transaction.

## Regression evidence

`tests/test_backend.py` exercises real handlers and temporary SQLite while
controlling only PDF/Graph boundaries. On the original baseline, 8 of 13 test
methods failed (11 assertions including subcases); 5 compatibility controls
passed. With the repairs, all 13 pass. Cases include legacy omission, ambiguous
and duplicate row changes, explicit clear/delete/reset, old tickets, failed
upload/retry, saves during rendering/upload, reversed overlapping upload timing,
and frozen/backwards clocks.

`scripts/verify_backend.py` additionally runs the real local HTTP service,
browser autosave/restoration/deletion/reset, unmodified PDF renderer, and Graph
code with external transport intercepted. It checks literal details and all
180 lines across a multipage PDF, and confirms a newer save stays queued while
an older PDF upload finishes. This is not a production Teams delivery test.
