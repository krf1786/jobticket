// Reset has no UI button; legacy reset helper checks invoke it directly.
// Local preview only. Real Date/input/reset/save behavior with synthetic state.
async (page) => {
  const origin = 'http://127.0.0.1:18765';
  const results = [], pageErrors = [], externalRequests = [];
  const assert = (ok, message) => { if (!ok) throw new Error(message); };
  async function run(name, timezoneId, instant, saved, date, test) {
    const context = await page.context().browser().newContext({ timezoneId });
    const p = await context.newPage();
    let stored = { jobName: saved ? 'Synthetic date test' : '', date, materials: ['Acrylic'], materialDetails: ['Keep detail'], materialCompleted: [true] };
    const saves = [];
    await p.clock.install({ time: new Date(instant) });
    await p.clock.pauseAt(new Date(new Date(instant).getTime() + 1000));
    p.on('pageerror', e => pageErrors.push({ name, message: e.message }));
    await p.route('**/*', async route => {
      const req = route.request(), u = new URL(req.url());
      if (u.origin !== origin) { externalRequests.push(req.url()); return route.abort(); }
      if (u.pathname === '/jobticket/' || u.pathname === '/jobticket/DEMO01') {
        const response = await route.fetch();
        const body = (await response.text()).replace(/window\.__TICKET__ = (.*?);<\/script>/, (_, raw) => {
          const boot = JSON.parse(raw); Object.assign(boot.state, stored);
          return 'window.__TICKET__ = ' + JSON.stringify(boot).replace(/</g, '\\u003c') + ';</script>';
        });
        return route.fulfill({ response, body });
      }
      if (u.pathname === '/jobticket/api/DEMO01' && req.method() === 'PUT') {
        stored = req.postDataJSON(); saves.push(stored);
        return route.fulfill({ json: { ok: true } });
      }
      if (u.pathname.includes('/api/')) return route.abort();
      return route.continue();
    });
    const advance = async ms => { await p.clock.runFor(ms); await p.waitForTimeout(50); };
    const currentDate = () => p.locator('#dateField').inputValue();
    try {
      await p.goto(origin + (saved ? '/jobticket/DEMO01' : '/jobticket/'));
      await advance(1000);
      await test({ p, advance, currentDate, saves, stored: () => stored });
      results.push({ name, passed: true });
    } catch (e) { results.push({ name, passed: false, error: e.message }); }
    finally { await context.close(); }
  }
  await run('New York scratch date uses local day after UTC midnight', 'America/New_York', '2026-10-23T01:30:00Z', false, '', async t => {
    assert(await t.currentDate() === '2026-10-22', 'Default date used UTC tomorrow');
    assert(t.saves.length === 0, 'Scratch default saved unexpectedly');
  });
  await run('Tokyo scratch date uses local day before UTC midnight', 'Asia/Tokyo', '2026-10-21T15:30:00Z', false, '', async t => {
    assert(await t.currentDate() === '2026-10-22', 'Default date used UTC yesterday');
  });
  await run('Blank saved date defaults without saving and persists on the next edit', 'America/New_York', '2026-10-22T16:00:00Z', true, '', async t => {
    assert(await t.currentDate() === '2026-10-22' && t.saves.length === 0, 'Blank saved default is missing or saved on load');
    await t.p.locator('#qtyField').fill('2'); await t.advance(1000);
    assert(t.saves.length > 0 && t.stored().date === '2026-10-22', 'Next edit did not save the default date');
    await t.p.reload(); await t.advance(1000);
    assert(await t.currentDate() === '2026-10-22', 'Saved default date did not survive reload');
  });
  await run('Saved historical date survives load and reload without an automatic save', 'America/New_York', '2026-10-22T16:00:00Z', true, '2026-08-12', async t => {
    assert(await t.currentDate() === '2026-08-12' && t.saves.length === 0, 'Stored date was replaced');
    await t.p.reload(); await t.advance(1000);
    assert(await t.currentDate() === '2026-08-12' && t.saves.length === 0, 'Reload changed stored date');
  });
  await run('Cancelled Reset keeps date; confirmed Reset saves today', 'America/New_York', '2026-10-22T16:00:00Z', true, '2026-08-12', async t => {
    await t.p.evaluate(() => { window.confirm = () => false; });
    await t.p.evaluate(() => resetTicket()); await t.advance(1000);
    assert(await t.currentDate() === '2026-08-12' && t.saves.length === 0, 'Cancelled Reset changed date');
    await t.p.evaluate(() => { window.confirm = () => true; });
    await t.p.evaluate(() => resetTicket()); await t.advance(1000);
    assert(await t.currentDate() === '2026-10-22' && t.stored().date === '2026-10-22', 'Confirmed Reset left today blank or unsaved');
  });
  await run('Reset after local midnight recomputes the new day', 'America/New_York', '2026-10-22T03:59:30Z', false, '', async t => {
    await t.p.locator('#dateField').fill('2026-10-21');
    await t.advance(60000);
    await t.p.evaluate(() => { window.confirm = () => true; });
    await t.p.evaluate(() => resetTicket());
    assert(await t.currentDate() === '2026-10-22', 'Reset did not recompute today after midnight');
  });
  return { passed: results.filter(r => r.passed).length, failed: results.filter(r => !r.passed).length, results, pageErrors, externalRequests };
}
