# Job-name print color — November 2, 2026

Source `4ae6bf6d37a3f95a2ec39371f885b4629212445e` changes only the default
`.job-name-input` color from white to light gray `#9ca3af`. The visible rich-text
editor inherits that default on screen and in print. Explicitly selected text
colors are preserved, Clear Formatting returns to gray, and both job numbers
remain red.

The original failure was reproduced in Chromium with print backgrounds off:
the job name had white PDF fill and disappeared on the white page. The corrected
PDF uses RGB `(156,163,175)` and its rendered first page was inspected. Custom
colors, Clear Formatting, red job numbers and no render-triggered saves were
also verified locally. Source hashes, JavaScript syntax, bootstrap safety and
preview routes pass. No new dependencies or permanent test framework were added.

Only `/root/jobticket/ticket.html` was backed up and atomically replaced at
**2026-11-03 02:07:20 UTC** (9:07 PM November 2 in New York). Public normalized
scratch/saved HTML and unchanged formatting assets match source. Both SQLite
backups passed integrity checks; all 25 ticket rows, attachment records and
corkboard data were unchanged, as were the service PID and 17 protected runtime
modules/assets. No backend, service, configuration or credential changes occurred.

The fresh public scratch page was also checked with `SB0861 - job name`: gray
on screen and in an actual PDF with backgrounds off, with both job numbers red.
The PDF raster was inspected. Its nine browser requests were GETs for the scratch
page and static assets; there were no writes, blocked requests or browser errors.
A final read-only audit confirmed all ticket, attachment and board rows unchanged.

Runtime template SHA256:
`573a42e5e178e4a3ce88d0a699a1cf7f0678e3ca3c37a6c798ad9d3f2736acf7`.

Private source/database backups and the receipt are in
`/root/jobticket/release-backups/name-grey-20261103T020702Z-217e3eca/`.
Guarded code-only rollback is prepared and was not run:

```sh
/root/jobticket/venv/bin/python -B /root/jobticket/release-backups/name-grey-20261103T020702Z-217e3eca/rollback.py
```

It restores only the template after source/config guards and retains all current
data, formatting assets and the running service. These results are separate from
GitHub CI or bot approval. Production Graph/renderer remain disabled and Teams/PDF
delivery remains unverified. No PR was merged; a GitHub merge does not deploy.
