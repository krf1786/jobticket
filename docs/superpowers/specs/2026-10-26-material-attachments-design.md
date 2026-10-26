# Material file attachments

Status: proposed for user approval; no product code changed.

## Outcome and approach

Attach production files directly to individual material rows, replacing the
shared-folder picker idea. Pasted links and shared-folder browsing were considered;
the user chose direct attachments so the ticket can carry its own file copy.

## Proposed behavior

- One file per material row, initially up to 50 MB. PDF, Illustrator and other
  production files are downloaded as files; uploaded content is not executed.
- A compact Attach file control in the material-details cell. Once attached,
  show its filename and Download, Replace and Remove controls. Empty rows keep
  their current compact height; filenames may add space on attached rows.
- Save the ticket before uploading a persistent attachment. Scratch tickets do
  not create server files silently.
- Stable row identifiers keep each attachment with its material, including
  duplicate material names, add/delete, replacement and reload. Failed or
  unfinished uploads must not replace an existing attachment.
- Replacing/removing a reference does not erase other ticket data. The initial
  release does not automatically delete uploaded bytes or old file versions.
- Print includes the filename; editing/upload controls stay hidden.

## Access and implementation boundaries

The current ticket app has no sign-in. A person who can access the ticket can
access its attachments; this proposal does not add private-user access controls.
Files are stored by the existing Job Ticket service with opaque file identifiers,
validated job ownership, bounded upload streaming and download-only responses.
Filenames are displayed as text and cannot control storage paths.

Use the existing FastAPI/SQLite and browser UI; no new dependencies or Graph/
Teams configuration. Preserve current corkboard integration, all existing tickets,
material details/completion, row behavior, date defaults, headers, image preview
and toolbar. Protect attachments against older tabs that omit new metadata;
reject ambiguous changes instead of attaching a file to the wrong material.

## Verification and release

Exercise real isolated upload/download bytes, size limits, invalid paths and
metadata, saved reload, duplicates, deletion during upload, replacement failure,
legacy saves, responsive layout, print and corkboard compatibility. Preserve
existing regression coverage. Only VERIFY-MATERIALS-20261021 may be used for
live write tests, and restore its exact state. Backend publication requires a
backed-up atomic release, service restart, guarded rollback and read-only data
comparison. Do not merge PR #2 automatically.
