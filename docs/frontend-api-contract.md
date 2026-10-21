# Frontend API expectations

These are observations from the captured client code, not a server
implementation or a verified production API specification. The local installer
corroborates some shapes but its deployed equivalence is unknown.

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
array of strings; a `steps` array of `{op, instr}` objects; and `image`, a URL
or null. Blank arrays are restored as one blank row. The frontend sends quantity
as a string and uses the native date/time input values.

## Requests made by the saved-mode client

All paths below start with `prefix + '/api/' + encodeURIComponent(jobId)`.

| Method and suffix | Request | Response consumed by the client |
| --- | --- | --- |
| `PUT` (no suffix) | JSON state; `Content-Type: application/json`, debounced 800ms after edits. | Requires a successful HTTP status and parseable JSON; body fields are not otherwise used. |
| `POST /image` | `FormData` with one `file` field. | Requires a successful HTTP status and JSON with `url`; displays that URL and queues a state save. |
| `GET /sync` | No body, initially and every 30 seconds when ready. | `error` selects failure; `stale` selects queued; otherwise `pushedAt` selects current/not-yet-pushed. |
| `POST /push` | No body; explicit Update Teams copy click. | JSON `ok` determines success or failure; dirty state triggers a save first. |

The client does not fetch initial state from a JSON endpoint; it receives it
in bootstrap. The historical installer also defines `GET /api/{job}`, health,
and upload-serving routes. Those were not required or probed for this capture.

Saved-mode number entry and job-name number extraction can navigate to
`prefix + '/' + encodedNumber`, optionally with a `name` query parameter.
The historical installer creates missing jobs on GET, so unknown job routes
must not be used as harmless live test fixtures. Only the already-provided
reference and blank root were read during capture.

## Unverified server responsibilities

Authentication/authorization, job ID validation, persistence/concurrency,
request limits, MIME/content validation, upload URLs, error schemas, Graph
permissions, SharePoint destination resolution, sync retries and PDF rendering
must be checked against the actual deployed service. The frontend's treatment
of responses does not establish what the server guarantees.

Local preview responses and browser mocks are explicitly synthetic and are
not production implementations of this contract.
