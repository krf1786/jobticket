# Frontend API expectations

These expectations were captured from the client and subsequently checked against
the deployed backend modules preserved in `backend/`. Integration tests use real
local SQLite/API/PDF code with external Graph transport intercepted. Production
verification and its limits are recorded in [backend-release.md](backend-release.md).

## Template input

The server replaces `__TITLE__` with escaped display text and `__BOOTSTRAP__`
with script-safe JSON. Never embed raw request data or credentials in either.

| Bootstrap field | Client use |
| --- | --- |
| `jobId` | Saved ticket identity; both red displays start from this value. |
| `jobName` | Server-provided display metadata; the form is restored from `state.jobName`. |
| `prefix` | Same-origin route prefix, observed as `/jobticket`. |
| `saving` | False selects scratch mode; true enables restore, autosave, upload, and saved-ticket navigation. |
| `state` | Form fields described below. |
| `sync.ready` | True adds Teams status, a push button, and a 30-second status poll. |

State has strings `jobName`, `date`, `qty`, `due`, `time`, `notes`; a `materials`
array of strings; a new `materialDetails` array of strings aligned by material
row index; `materialCompleted: boolean[]` aligned by the same index; a `steps` array of `{op, instr}` objects; and `image`, a URL
or null. Blank arrays are restored as one blank row. The frontend sends quantity
as a string and uses the native date/time input values. Tickets without
`materialDetails` retain their original materials and show blank details.
Missing, non-array, or non-string detail values become blank fields. Completion
is checked only for literal `true`; absent/invalid values restore unchecked.

`materialDetails` is a frontend branch addition stored in the backend's existing
JSON state. The repaired backend preserves it and completion when an older payload omits
either field and keeps the same materials. An older payload that changes material rows
with nonempty omitted details or checked completion receives HTTP 409 without any write. Updated payloads
include the field explicitly and can clear/delete/reset normally. This protects
additive details; it is not general multi-client conflict resolution. See
[backend-fixes.md](backend-fixes.md).

## Requests made by the saved-mode client

All paths below start with `prefix + '/api/' + encodeURIComponent(jobId)`.

| Method and suffix | Request | Response consumed by the client |
| --- | --- | --- |
| `PUT` (no suffix) | JSON state; `Content-Type: application/json`, debounced 800ms after edits; requests are serialized and newer local revisions are drained in order. | Requires a successful HTTP status and parseable JSON; only the revision actually sent is acknowledged as saved. |
| `POST /image` | `FormData` with one `file` field. | Requires a successful HTTP status and JSON with `url`; displays that URL and queues a state save. |
| `GET /sync` | No body, initially and every 30 seconds when ready. | `error` selects failure; `stale` selects queued; otherwise `pushedAt` selects current/not-yet-pushed. |
| `POST /push` | No body; explicit Update Teams copy click; waits for all current local edits to save successfully. No request is dispatched if saving fails. | Successful HTTP status and JSON `ok` are required. A completion for an older local revision cannot mark newer edits current. |

These save/push sequencing fixes are documented separately in
[review-fixes.md](review-fixes.md). Those fixes left route paths and payload
shapes unchanged; the subsequent [material-details change](material-details.md)
adds only the state field described above and no new endpoint.
Local revision counters are not sent to the server and do not provide
cross-client locking or server-side snapshot/version guarantees.

The client does not fetch initial state from a JSON endpoint; it receives it
in bootstrap. The verified backend also defines `GET /api/{job}`, health, and upload-serving
routes. API GET returns 404 for missing jobs without creating them.

Saved-mode number entry and job-name number extraction can navigate to
`prefix + '/' + encodedNumber`, optionally with a `name` query parameter.
The deployed page route creates missing jobs on GET, so unknown job routes
must not be used as harmless live test fixtures. Only the already-provided
reference and blank root were read during capture.

## Remaining verification boundaries

Authentication/authorization, request/upload limits, MIME/content validation,
and Graph permissions were not broadened or audited by this scoped change.
SharePoint delivery remains unverified because production Graph configuration
and the optional PDF dependencies are missing. The frontend's treatment
of responses does not establish what the server guarantees.

Local preview responses and browser mocks are explicitly synthetic and are
not production implementations of this contract.
