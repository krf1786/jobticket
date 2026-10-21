# Reviewed client fixes

The original capture is immutable at
[`57f8f6b28005d7511b67fc95c40b6bbd7695bd69`](https://github.com/krf1786/jobticket/blob/57f8f6b28005d7511b67fc95c40b6bbd7695bd69/frontend/ticket.html),
with template SHA-256
`bf0ad0ab27a84ce2d6b69f805e950f49d47f262b14d0808ec19b3d429cc11af1`.
The working template includes the following user-approved changes from that
baseline. No live service has been changed.

## Changes

1. [Reset cancellation](https://github.com/krf1786/jobticket/pull/1#discussion_r4342505997):
   removed the wrapper that cleared `currentImageUrl` before confirmation.
   The original Reset function already asks first, then calls the image-removal
   hook and changes table rows. Those existing hooks save confirmed resets.
   Cancelling now neither alters the image reference nor schedules a save.
2. [Overlapping saves](https://github.com/krf1786/jobticket/pull/1#discussion_r4342506013):
   each change increments a local revision. One PUT runs at a time; its response
   acknowledges only the revision whose state it sent. Newer edits remain dirty
   and are collected by the next serialized save. A failed request leaves
   unload protection active and reports failure; a subsequent edit or Teams
   retry can save again. A completed save returns success only after draining
   all newer local revisions.
3. [Teams push sequencing](https://github.com/krf1786/jobticket/pull/1#discussion_r4342506003):
   replaced the fixed 900ms delay with the save queue's completion. Save failure
   prevents the push. Duplicate clicks are disabled while saving/pushing.
   Edits made after push dispatch cannot be certified by that push's result,
   even if those edits finish saving before the push returns. Poll responses
   started before a newer edit or explicit push are also ignored.

At fix commit `6ef71bb`, the visual template, both red number displays,
API paths/payloads, historical HTML files, and scratch-mode behavior were unchanged.
The later [material-details change](material-details.md) adds a field and layout
while preserving these three fixes. The backend is still
unverified. Local revisions protect this browser's save sequencing; they do
not establish server-side atomic snapshots, cross-tab/client concurrency, or
the state of Microsoft Teams/SharePoint.

## Regression evidence

The tests execute the real frontend in Chromium. HTTP responses are held and
released explicitly, and the browser clock advances debounce/poll timers
deterministically. Every non-local request is blocked. Fixtures are synthetic.

| Stage | Result |
| --- | --- |
| Original captured code, before fixes | 1 passed / 9 failed; confirmed Reset was the passing control. |
| Reset fix only | 3 passed / 7 failed; both cancellation failures were removed. |
| Revision-aware saves, before Teams fix | 5 passed / 5 failed. |
| Two additional Teams race tests, before Teams fix | 5 passed / 7 failed. |
| All three fixes | 12 passed / 0 failed; zero page errors or external requests. |

Coverage: cancelled Reset emits no PUT; image survives the next real edit;
confirmed Reset saves; old save completion retains newer unload protection;
failed follow-up remains dirty and can retry; slow saves delay Teams pushes;
failed initial/latest saves prevent pushes; edits during awaited saves are
drained first; edits during an in-flight push invalidate its result; and old
sync polling cannot label dirty edits current.

To reproduce (fresh Playwright CLI session, local preview already running):

```sh
playwright-cli -s=jobticket-regression open about:blank
playwright-cli -s=jobticket-regression --raw run-code \
  --filename=scripts/save-regressions.js
playwright-cli -s=jobticket-regression close
```

The returned JSON must report `failed: 0`, `passed: 12`, empty `pageErrors`,
and empty `externalRequests`. The script returns every case's result so baseline
failures can be inspected together; do not use the CLI process exit code alone
as the test verdict. The clock is resumed before returning for CLI cleanup.
