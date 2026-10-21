// Playwright CLI: run-code --filename=scripts/save-regressions.js (fresh session).
// Start preview.py --port 18765. Real template/DOM; only HTTP is mocked.
// Clock control makes the debounce and old 900ms push race deterministic.
async (page) => {
  const origin = 'http://127.0.0.1:18765';
  const image = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg"/%3E';
  const results = [], external = [], pageErrors = [];
  const assert = (value, message) => { if (!value) throw new Error(message); };
  await page.clock.install({ time: new Date('2026-10-21T12:00:00Z') });
  await page.clock.pauseAt(new Date('2026-10-21T12:01:00Z'));

  async function scenario(name, test) {
    const p = await page.context().newPage();
    const saves = [], pushes = [], polls = [];
    let holdPolls = false;
    const eventually = async (predicate, message) => {
      for (let i = 0; i < 100; i++) {
        if (await predicate()) return;
        await p.waitForTimeout(10);
      }
      throw new Error(message);
    };
    const advance = async ms => { await p.clock.runFor(ms); await p.waitForTimeout(30); };
    const status = () => p.locator('#saveStatus').textContent();
    const teams = () => p.locator('#teamsStatus').textContent();
    const guarded = () => p.evaluate(() => {
      const event = new Event('beforeunload', { cancelable: true });
      window.dispatchEvent(event);
      return event.defaultPrevented;
    });
    const replySave = async (index, code = 200) => {
      await saves[index].route.fulfill({ status: code, contentType: 'application/json', body: JSON.stringify(code === 200 ? { ok: true, savedAt: 1 } : { error: 'Synthetic save failure' }) });
      await p.waitForTimeout(30);
    };
    const replyPush = async index => {
      await pushes[index].fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' });
      await p.waitForTimeout(30);
    };
    const clickTeams = () => p.getByRole('button', { name: 'Update Teams copy' }).evaluate(button => button.click());
    p.on('pageerror', error => pageErrors.push({ name, message: error.message }));
    await p.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.origin !== origin) {
        external.push(request.url());
        return route.abort('blockedbyclient');
      }
      if (url.pathname === '/jobticket/DEMO01') {
        const response = await route.fetch();
        const body = (await response.text()).replace(/window\.__TICKET__ = (.*?);<\/script>/, (_, payload) => {
          const boot = JSON.parse(payload);
          boot.state.image = image;
          return 'window.__TICKET__ = ' + JSON.stringify(boot).replace(/</g, '\\u003c') + ';</script>';
        });
        return route.fulfill({ response, body });
      }
      if (url.pathname === '/jobticket/api/DEMO01' && request.method() === 'PUT') {
        saves.push({ route, state: request.postDataJSON() });
        return;
      }
      if (url.pathname.endsWith('/push')) { pushes.push(route); return; }
      if (url.pathname.endsWith('/sync')) {
        if (holdPolls) { polls.push(route); return; }
        return route.fulfill({ json: { ready: true, error: '', stale: false, pushedAt: 1 } });
      }
      if (url.pathname.startsWith('/jobticket/api/')) return route.abort('blockedbyclient');
      return route.continue();
    });
    try {
      await p.goto(origin + '/jobticket/DEMO01?teams=1');
      await advance(1);
      await eventually(async () => (await status()) === 'Saved', 'Fixture did not finish restoring');
      await eventually(async () => (await teams()) === 'Teams: copy current', 'Fixture sync did not finish');
      await test({ p, saves, pushes, polls, advance, eventually, status, teams, guarded, replySave, replyPush, clickTeams, holdPolls: () => { holdPolls = true; } });
      results.push({ name, passed: true });
    } catch (error) {
      results.push({ name, passed: false, error: error.message });
    } finally {
      await p.close();
    }
  }

  await scenario('Cancelled Reset schedules no save', async t => {
    await t.p.evaluate(() => { window.confirm = () => false; });
    await t.p.getByRole('button', { name: 'Reset', exact: false }).evaluate(b => b.click());
    await t.advance(1200);
    assert(t.saves.length === 0, 'Cancelling Reset still emitted a PUT');
    assert(!(await t.guarded()), 'Cancelling Reset dirtied an unchanged ticket');
  });

  await scenario('Cancelled Reset preserves image in the next real edit', async t => {
    await t.p.evaluate(() => { window.confirm = () => false; });
    await t.p.getByRole('button', { name: 'Reset', exact: false }).evaluate(b => b.click());
    await t.p.locator('#notes').fill('Edit after cancelled reset');
    await t.advance(800);
    await t.eventually(() => t.saves.length === 1, 'Expected the real edit to save');
    assert(t.saves[0].state.image === image, 'Cancelled Reset cleared the saved image reference');
    assert(await t.p.locator('#imgPreview').isVisible(), 'Cancelled Reset hid the image');
  });

  await scenario('Confirmed Reset clears and saves the ticket', async t => {
    await t.p.evaluate(() => { window.confirm = () => true; });
    await t.p.getByRole('button', { name: 'Reset', exact: false }).evaluate(b => b.click());
    await t.advance(800);
    await t.eventually(() => t.saves.length === 1, 'Confirmed Reset did not save');
    assert(t.saves[0].state.image === null && t.saves[0].state.jobName === '', 'Confirmed Reset retained cleared fields');
    await t.replySave(0);
    await t.eventually(async () => !(await t.guarded()), 'Confirmed Reset did not become clean after save');
  });

  await scenario('Older save success keeps newer edits dirty', async t => {
    await t.p.locator('#notes').fill('First revision');
    await t.advance(800);
    await t.eventually(() => t.saves.length === 1, 'First save missing');
    await t.p.locator('#notes').fill('Newer revision');
    await t.advance(800);
    assert(t.saves.length === 1, 'Concurrent PUTs can overwrite newer state');
    await t.replySave(0);
    assert(await t.guarded(), 'Older save cleared unload protection for newer edits');
    assert(!/^Saved/.test(await t.status()), 'Older save incorrectly reported newer edits as saved');
    await t.advance(200);
    await t.eventually(() => t.saves.length === 2, 'Newer revision was not queued');
    assert(t.saves[1].state.notes === 'Newer revision', 'Queued save lost newer form values');
    await t.replySave(1);
    await t.eventually(async () => !(await t.guarded()), 'Latest successful save did not clear dirty state');
  });

  await scenario('Failed follow-up save retains unload protection and can retry', async t => {
    await t.p.locator('#notes').fill('First revision');
    await t.advance(800);
    await t.eventually(() => t.saves.length === 1, 'First save missing');
    await t.p.locator('#notes').fill('Newer revision');
    await t.advance(800);
    await t.replySave(0);
    await t.advance(200);
    await t.eventually(() => t.saves.length === 2, 'Follow-up save missing');
    await t.replySave(1, 503);
    await t.eventually(async () => (await t.status()).includes('Not saved'), 'Failed follow-up had no error state');
    assert(await t.guarded(), 'Failed newer save has no unload protection');
    await t.p.locator('#notes').fill('Retry revision');
    await t.advance(800);
    await t.eventually(() => t.saves.length === 3, 'Retry save missing');
    await t.replySave(2);
    await t.eventually(async () => !(await t.guarded()), 'Successful retry remained dirty');
  });

  await scenario('Teams waits for a slow save and sends only one push', async t => {
    await t.p.locator('#notes').fill('Latest revision');
    await t.clickTeams();
    await t.eventually(() => t.saves.length === 1, 'Push did not request a save');
    await t.clickTeams();
    await t.advance(1500);
    assert(t.pushes.length === 0, 'Teams push ran before a slow save completed');
    await t.replySave(0);
    await t.eventually(() => t.pushes.length === 1, 'Latest saved revision was not pushed exactly once');
    await t.replyPush(0);
    await t.eventually(async () => (await t.teams()) === 'Teams: copy current', 'Successful current push not reflected');
    await t.advance(1200);
    assert(t.saves.length === 1 && t.pushes.length === 1, 'Clicking push duplicated save or push requests');
  });

  await scenario('Teams does not push after a failed save', async t => {
    await t.p.locator('#notes').fill('Unstored revision');
    await t.clickTeams();
    await t.eventually(() => t.saves.length === 1, 'Push did not request save');
    await t.replySave(0, 503);
    await t.advance(1500);
    assert(t.pushes.length === 0, 'Teams push ran despite failed save');
    assert(await t.guarded(), 'Failed save lost unload protection');
    assert((await t.teams()) !== 'Teams: copy current', 'Failed save was reported as current');
  });

  await scenario('Teams drains edits made during the awaited save before pushing', async t => {
    await t.p.locator('#notes').fill('First revision');
    await t.clickTeams();
    await t.eventually(() => t.saves.length === 1, 'Initial save missing');
    await t.p.locator('#notes').fill('Latest revision');
    await t.advance(800);
    await t.replySave(0);
    await t.advance(1000);
    await t.eventually(() => t.saves.length === 2, 'Newer revision was not saved');
    assert(t.saves[1].state.notes === 'Latest revision', 'Follow-up did not collect latest values');
    assert(t.pushes.length === 0, 'Teams pushed while the latest revision was still unsaved');
    await t.replySave(1);
    await t.eventually(() => t.pushes.length === 1, 'Teams did not push after latest save');
    await t.replyPush(0);
  });

  await scenario('Edits made during a push are never labelled current', async t => {
    await t.clickTeams();
    await t.advance(1);
    await t.eventually(() => t.pushes.length === 1, 'Clean ticket did not push');
    await t.p.locator('#notes').fill('Edit made after push started');
    await t.replyPush(0);
    assert((await t.teams()) !== 'Teams: copy current', 'Old push completion marked newer edits current');
    assert(await t.guarded(), 'Edit during push lost unload protection');
  });

  await scenario('A failed latest revision prevents a waiting Teams push', async t => {
    await t.p.locator('#notes').fill('First revision');
    await t.clickTeams();
    await t.eventually(() => t.saves.length === 1, 'Initial save missing');
    await t.p.locator('#notes').fill('Latest revision');
    await t.replySave(0);
    await t.advance(800);
    await t.eventually(() => t.saves.length === 2, 'Latest save missing');
    await t.replySave(1, 503);
    await t.advance(1500);
    assert(t.pushes.length === 0, 'Teams pushed after the latest save failed');
    assert(await t.guarded(), 'Failed latest save lost unload protection');
  });

  await scenario('Even saved newer edits invalidate an older push result', async t => {
    await t.clickTeams();
    await t.advance(1);
    await t.eventually(() => t.pushes.length === 1, 'Initial push missing');
    await t.p.locator('#notes').fill('Saved after push started');
    await t.advance(800);
    await t.eventually(() => t.saves.length === 1, 'Newer save missing');
    await t.replySave(0);
    await t.eventually(async () => !(await t.guarded()), 'Newer save did not finish');
    await t.replyPush(0);
    assert((await t.teams()) !== 'Teams: copy current', 'Old push was reported current after a newer revision saved');
  });

  await scenario('An older sync poll cannot mark dirty edits current', async t => {
    t.holdPolls();
    await t.advance(30000);
    await t.eventually(() => t.polls.length > 0, 'Expected scheduled sync poll');
    await t.p.locator('#notes').fill('New unsaved revision');
    await t.polls[0].fulfill({ json: { ready: true, error: '', stale: false, pushedAt: 1 } });
    await t.p.waitForTimeout(30);
    assert((await t.teams()) !== 'Teams: copy current', 'Older poll marked unsaved edits current');
  });

  // Let the CLI finish its own post-command UI bookkeeping on the main tab.
  await page.clock.resume();
  return { passed: results.filter(r => r.passed).length, failed: results.filter(r => !r.passed).length, results, pageErrors, externalRequests: external };
}
