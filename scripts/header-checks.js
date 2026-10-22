// Real template with synthetic, intercepted localhost state only.
async (page) => {
  const origin = 'http://127.0.0.1:18765';
  const results = [], pageErrors = [], externalRequests = [];
  const assert = (ok, message) => { if (!ok) throw new Error(message); };
  async function run(name, saved, initial, test) {
    const p = await page.context().newPage();
    p.setDefaultTimeout(3000);
    let state = { jobName: '', materials: ['Acrylic'], materialDetails: ['Keep details'], materialCompleted: [true], ...initial };
    const puts = [], navigations = [];
    p.on('pageerror', e => pageErrors.push({ name, message: e.message }));
    await p.route('**/*', async route => {
      const req = route.request(), u = new URL(req.url());
      if (u.origin !== origin) { externalRequests.push(req.url()); return route.abort(); }
      if (u.pathname === '/jobticket/DEMO01' || u.pathname === '/jobticket/') {
        const response = await route.fetch();
        const body = (await response.text()).replace(/window\.__TICKET__ = (.*?);<\/script>/, (_, raw) => {
          const boot = JSON.parse(raw); boot.state = state;
          return 'window.__TICKET__ = ' + JSON.stringify(boot).replace(/</g, '\\u003c') + ';</script>';
        });
        return route.fulfill({ response, body });
      }
      if (u.pathname === '/jobticket/api/DEMO01' && req.method() === 'PUT') {
        state = req.postDataJSON(); puts.push(state); return route.fulfill({ json: { ok: true } });
      }
      if (/^\/jobticket\/SB\d+$/.test(u.pathname)) {
        navigations.push(u.pathname + u.search);
        return route.fulfill({ contentType: 'text/html', body: '<p>Intercepted synthetic navigation</p>' });
      }
      if (u.pathname.startsWith('/jobticket/api/')) return route.abort();
      return route.continue();
    });
    const pair = async value => {
      assert(await p.locator('#jobNo').inputValue() === value, 'Left job number mismatch');
      assert(await p.locator('#jobNoRight').textContent() === value, 'Right job number mismatch');
      const styles = await p.evaluate(() => [jobNo, jobNoRight].map(n => { const s = getComputedStyle(n); return { color: s.color, size: s.fontSize, display: s.display }; }));
      assert(styles.every(s => s.color === 'rgb(239, 68, 68)' && s.display !== 'none') && styles[0].size === '46px' && styles[1].size === '26px', 'Both corners must remain visibly red at original sizes');
    };
    try {
      await p.goto(origin + (saved ? '/jobticket/DEMO01' : '/jobticket/'));
      await test({ p, pair, puts, navigations, state: () => state });
      results.push({ name, passed: true });
    } catch (e) { results.push({ name, passed: false, error: e.message }); }
    finally { await p.close(); }
  }
  await run('Scratch job-name input fills both red numbers without saving or navigation', false, {}, async t => {
    const placeholder = await t.p.locator('#jobNo').evaluate(n => getComputedStyle(n, '::placeholder').color);
    assert(placeholder === 'rgb(239, 68, 68)', 'Empty scratch number placeholder should remain red');
    await t.p.locator('#jobName').fill('sb-4321 - Synthetic header'); await t.pair('SB4321');
    await t.p.locator('#jobName').press('Enter'); await t.p.waitForTimeout(1000);
    assert(t.puts.length === 0 && t.navigations.length === 0 && t.p.url().endsWith('/jobticket/'), 'Scratch header entry must not create or save a ticket');
  });
  await run('Scratch direct number edits update right mirror and print', false, {}, async t => {
    await t.p.locator('#jobNo').fill('sb9876');
    assert(await t.p.locator('#jobNoRight').textContent() === 'SB9876', 'Direct scratch number edit did not update mirror');
    await t.p.locator('#jobName').fill('SB9876 synthetic'); await t.pair('SB9876');
    await t.p.emulateMedia({ media: 'print' }); await t.pair('SB9876');
    assert(await t.p.locator('.toolbar').isHidden(), 'Print toolbar should stay hidden');
    await t.p.screenshot({ path: 'output/playwright/header-scratch-print.png', fullPage: true });
  });
  await run('Saved job identity keeps both original red displays', true, { jobName: 'Synthetic without number' }, async t => {
    await t.pair('DEMO01'); await t.p.waitForTimeout(1000);
    assert(t.puts.length === 0, 'Header bootstrap caused an unwanted save');
    await t.p.emulateMedia({ media: 'print' }); await t.pair('DEMO01');
  });
  await run('Saved identity wins over a different number in the restored name', true, { jobName: 'SB2468 - Restored synthetic' }, async t => {
    await t.pair('DEMO01'); await t.p.waitForTimeout(1000);
    assert(t.puts.length === 0, 'Name extraction during restore should not autosave');
    await t.p.reload(); await t.pair('DEMO01');
    assert(await t.p.getByRole('checkbox', { name: 'Completed 1', exact: true }).isChecked(), 'Header restore disturbed completion');
    await t.p.emulateMedia({ media: 'print' }); await t.pair('DEMO01');
  });
  await run('Saved name edits persist while reload restores ticket identity and navigation', true, { jobName: 'Synthetic' }, async t => {
    await t.p.locator('#jobName').fill('sb 4321 - Edited synthetic'); await t.pair('SB4321');
    await t.p.waitForFunction(() => /^Saved/.test(saveStatus.textContent));
    assert(t.puts.length > 0 && t.state().jobName === 'sb 4321 - Edited synthetic', 'Saved name edit did not persist');
    await t.p.reload(); await t.pair('DEMO01');
    await t.p.locator('#jobName').press('Enter'); await t.p.waitForURL('**/SB4321?*');
    assert(t.navigations.length === 1 && new URL(t.p.url()).searchParams.get('name') === t.state().jobName, 'Saved Enter navigation changed');
  });
  await run('Saved direct number edits retain mirror and Enter navigation', true, { jobName: 'Synthetic' }, async t => {
    await t.p.locator('#jobNo').fill('sb5555');
    assert(await t.p.locator('#jobNoRight').textContent() === 'SB5555', 'Saved direct mirror changed');
    await t.p.waitForFunction(() => /^Saved/.test(saveStatus.textContent));
    await t.p.locator('#jobNo').press('Enter'); await t.p.waitForURL('**/SB5555?*');
    assert(t.navigations.length === 1, 'Saved direct Enter navigation missing');
  });
  return { passed: results.filter(r => r.passed).length, failed: results.filter(r => !r.passed).length, results, pageErrors, externalRequests };
}
