# Material attachments

On a saved ticket, click the paperclip in a material's Details cell and choose
one or several production files. Each file can be up to **100 MB (104,857,600 bytes)**.
The paperclip stays available to add more files to the same row. Click a filename
to download that original file. Each file has its own Replace and Remove controls;
changing one leaves the other files intact. Existing uploaded versions are retained. Scratch
tickets must become saved tickets before files can be attached.

Attachments save with their row and restore on reload. Duplicate material names
use stable row identifiers. A failed/oversized replacement keeps the previous
attachments. A selection uploads sequentially, one file per request; a failed or
oversized file is identified by name and the other valid files can still upload.
Deleting a row during an upload cancels the remaining selection and cannot
move the returned file to another row. Enter still adds rows from Material or
Details; Enter on file controls activates that control. Empty rows retain the
compact height. Mobile filenames have their own line above Replace/Remove.
Print shows every filename, without editing controls or broken local links.

## Storage and compatibility

The existing FastAPI service stores files under `attachments/` using opaque IDs
and canonical metadata in a separate `attachments` table in `tickets.db`. The
original filename never selects a storage path. Downloads require the owning
job/file IDs and use attachment disposition, octet-stream and nosniff headers.
File content is not executed. Existing ticket access is unchanged: there is no
new sign-in or per-user privacy layer. No Graph credentials, Teams setup or new
production dependencies are required.

Ticket JSON uses aligned `materialRowIds: string[]` and
`materialFiles: {id,name,size,url}[][]`, with an empty list for unattached rows.
Legacy `null` or single-file object entries still load and save without an eager
data migration. New saves also carry a request-only `materialFileBase` map of
acknowledged ordered file-ID lists; old `null`/single-ID baselines remain accepted.
The backend validates every reference
against the owning registry and strips that map before storage. A stale modern
save returns409 rather than clearing/replacing a newer reference. Legacy saves
omitting attachment fields preserve them when all material arrays are unchanged;
ambiguous row changes with attachments return409. Reload the updated ticket
before retrying a conflict. Duplicate IDs within a row, foreign files and
malformed references are rejected. This is attachment protection, not full collaborative
editing conflict resolution.

The file limit is enforced separately from multipart framing. A scoped ASGI
receive guard also bounds total attachment POST bodies to101 MiB, including
requests with absent/incorrect declared lengths, before unbounded temp spooling.
New directories are0750 and stored bytes0600. Rejected/failed storage removes only
the new partial file. No automatic cleanup deletes retained versions.

The compatible backend must remain installed once list-shaped attachments have
been saved. A downgrade to the original single-file backend must refuse those
states rather than silently losing references. Release rollback checks that
condition and never restores an old database over newer ticket edits.

## Verification

Run `python -m unittest discover -s tests -v` for backend/storage regressions.
Run `python scripts/attachment-checks.py` using the existing release-check Python
and Playwright browser cache for the real isolated API/SQLite/browser workflow.
The harness copies only source/static into temporary directories, has no Graph
credentials and never accesses production. Existing browser checks use the
loopback-only `scripts/preview.py`. See [the multiple-file release evidence](multiple-attachments-release.md)
and [the original storage release](attachments-release.md).
