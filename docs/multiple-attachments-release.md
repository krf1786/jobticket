# Multiple material attachments — November 3, 2026

Source `7dc5b0372ac4ebf129df1b93c05fe2ebe4c5495a` is live. Each material row
accepts multiple files through its paperclip, including selecting several at
once. The paperclip stays available for later additions. Each file has its own
download, Replace and Remove actions. The limit remains 100 MB per file, with
sequential individual upload requests. Partial failures retain existing files
and identify the failed filename while other valid selections can finish.

Existing single-file values and old client baselines remain supported. New
saves use ordered file lists and complete acknowledged ID lists; stale saves
cannot remove a newer file. Each reference is canonicalized against its owning
ticket. There is no eager ticket migration, storage/schema change or dependency
installation. See [the attachment contract](material-attachments.md).

Verification passed 71 backend/storage tests, 41 isolated real API/browser checks
and all 50 existing formatting integration checks. Tests first reproduced the
single-file limitation. Coverage includes exact upload limits, original-byte
downloads, independent replacement/removal, duplicate filenames, partial failure,
row deletion during upload, delayed saves, stale tabs, legacy reloads and compact
empty rows. Desktop, 390/320px layouts and actual printed PDFs were inspected.
Source hashes, script syntax, bootstrap safety and preview routes pass.
Independent review found no actionable issues.

Only attachments.py, static/material-attachments.js and ticket.html changed at
runtime. They were backed up and published at **2026-11-03 21:54:31 UTC**
(4:54 PM New York). Consistent backups of both databases passed integrity checks.
The compatible backend was restarted once before publishing the new client.
All 27 existing ticket rows were unchanged at publication. Fifteen protected
modules/assets, Caddy/service configuration, Graph and renderer stayed unchanged.

All 17 live browser checks passed using only `VERIFY-MATERIALS-20261021`, with
four small synthetic uploads and four ticket PUTs. Browser downloads returned
the exact selected bytes; individual Replace/Remove, reload, viewport bounds and
printed filenames passed. There were no browser errors or unauthorized requests.

The synthetic ticket's exact original JSON, columns and timestamps were restored
at **21:57:16 UTC**, and all four owned upload records/byte files were removed.
The cleanup guard first detected the editor's existing blank-time autofill; the
private helper was narrowed to permit valid autofill only for an originally
blank time, with exact final revision/state checks retained. All 22 isolated
helper checks passed, including rejection of nonblank time changes. Final
read-only audits confirmed all 27 ticket rows, attachment registry/storage and
corkboard rows unchanged. No customer ticket was written.

Runtime SHA256:

- attachments.py: `b5cd554f837993938b2aeb754e144f21218f5e306445a4643a89026bb9cf752d`
- material-attachments.js: `e91f4760da57cc6173c25403351e6c74020d56fd067d8f1780764fddaaeb4668`
- ticket.html: `5d0d7a66375e92a3cd62147ef225cb5dc361283df3786710471ea8b9e3c37e3b`

Private code/database backups and the release receipt are in
`/root/jobticket/release-backups/multi-attachments-20261103T215408Z-0fcd8a69/`.
Guarded code-only rollback is prepared and was not invoked:

```sh
/root/jobticket/venv/bin/python -B /root/jobticket/release-backups/multi-attachments-20261103T215408Z-0fcd8a69/rollback.py
```

The previous backend cannot read list-shaped attachment data. Rollback refuses
to downgrade while any such state exists, checking again after stopping the
service. Retain the compatible backend and prepare a forward fix in that case.
No rollback restores an old database over newer edits. Production Graph/renderer
remain disabled; browser PDF checks do not verify production Teams/PDF delivery.
These checks are separate from GitHub CI/bot approval. No PR was merged.
