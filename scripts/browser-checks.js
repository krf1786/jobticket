// Reset has no UI button; legacy reset helper checks invoke it directly.
// Run with Playwright CLI run-code --filename=scripts/browser-checks.js.
// Start scripts/preview.py --port 18765 first. Uses synthetic data only.
async (page) => {
  const origin = 'http://127.0.0.1:18765';
  const requests = [], errors = [], blocked = [], checks = [];
  let failSave = false, failPush = false;
  const image = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="60"><rect width="100" height="60" fill="skyblue"/></svg>');
  const check = (condition, message) => {
    if (!condition) throw new Error(message);
    checks.push(message);
  };
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin !== origin) {
      blocked.push(request.url());
      return route.abort('blockedbyclient');
    }
    if (url.pathname.startsWith('/jobticket/api/')) {
      requests.push({ method: request.method(), path: url.pathname, body: request.postData() });
      let status = 200, json = { ok: true };
      if (url.pathname.endsWith('/sync')) json = { error: '', stale: false, pushedAt: 1 };
      else if (url.pathname.endsWith('/image')) json = { url: image };
      else if (url.pathname.endsWith('/push')) json = { ok: !failPush };
      else if (failSave) { status = 503; json = { error: 'Synthetic failure' }; }
      return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(json) });
    }
    // Observe navigation without requesting an unknown ticket from any service.
    if (url.pathname === '/jobticket/SB1234') {
      return route.fulfill({ status: 200, contentType: 'text/html', body: '<p>Synthetic navigation destination</p>' });
    }
    return route.continue();
  });
  const waitSaved = () => page.waitForFunction(() => /^Saved/.test(document.querySelector('#saveStatus').textContent));
  const loadSaved = async (teams = false) => {
    await page.goto(origin + '/jobticket/DEMO01' + (teams ? '?teams=1' : ''));
    await waitSaved();
  };

  await page.goto(origin + '/jobticket/');
  check(await page.locator('#saveStatus').textContent() === 'Scratch ticket · not saved', 'Scratch mode is visibly unsaved');
  await page.locator('#jobName').fill('Scratch demonstration');
  await page.waitForTimeout(1000);
  check(requests.length === 0, 'Scratch edits make no API requests');

  await loadSaved();
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(950);
  check(requests.length === 0, 'Restoring saved bootstrap makes no save/upload/push requests');
  check(await page.locator('#jobNo').inputValue() === 'DEMO01', 'Left number uses bootstrap jobId');
  check(await page.locator('#jobNoRight').textContent() === 'DEMO01', 'Right number uses bootstrap jobId');
  const styles = await page.evaluate(() => ['jobNo', 'jobNoRight'].map(id => {
    const style = getComputedStyle(document.getElementById(id));
    return { size: style.fontSize, color: style.color };
  }));
  check(styles[0].size === '46px' && styles[1].size === '26px' && styles.every(s => s.color === 'rgb(239, 68, 68)'), 'Both red numbers retain the live sizes and color');
  check(await page.locator('#teamsStatus').count() === 0, 'sync.ready=false hides Teams controls');
  await page.setViewportSize({ width: 1200, height: 1300 });
  await page.screenshot({ path: 'output/playwright/saved-demo.png', fullPage: true });

  await page.locator('#jobName').fill('Synthetic production example');
  await page.locator('#qtyField').fill('3');
  await page.locator('#notes').fill('Synthetic verification notes');
  await page.locator('#matBody input[data-row-input="mat"]').first().fill('Sample material');
  await page.locator('#matBody input[data-row-input="mat"]').first().press('Enter');
  await page.locator('#prodBody input').first().fill('Sample operation');
  await page.locator('#prodBody textarea').first().fill('Sample instructions');
  await waitSaved();
  const saves = requests.filter(r => r.method === 'PUT');
  const state = JSON.parse(saves.at(-1).body);
  check(state.jobName === 'Synthetic production example' && state.qty === '3' && state.notes === 'Synthetic verification notes' && state.materials[0] === 'Sample material' && state.steps[0].instr === 'Sample instructions', 'Autosave collects editable form state into mocked PUT');
  check(await page.locator('#matBody tr').count() === 2, 'Enter adds a material row');

  await page.locator('#jobNo').fill('sb1234');
  check(await page.locator('#jobNoRight').textContent() === 'SB1234', 'Editing left number updates normalized right mirror');
  await waitSaved();
  await page.locator('#jobNo').press('Enter');
  await page.waitForURL('**/jobticket/SB1234?*');
  check(new URL(page.url()).searchParams.get('name') === 'Synthetic production example', 'Enter navigates using normalized number and encoded name');

  await loadSaved();
  await page.locator('#jobName').fill('SB-4321 Synthetic example');
  check(await page.locator('#jobNo').inputValue() === 'SB4321' && await page.locator('#jobNoRight').textContent() === 'SB4321', 'Job-name extraction updates both number displays');
  await waitSaved();
  await page.locator('#imgInput').setInputFiles({ name: 'synthetic.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="60"/>') });
  await page.waitForFunction(() => document.querySelector('#imgPreview').style.display === 'block');
  await waitSaved();
  check(requests.some(r => r.path.endsWith('/image') && r.method === 'POST' && r.body.includes('name="file"')), 'Image selection posts multipart file only to a mocked endpoint');
  check(JSON.parse(requests.filter(r => r.method === 'PUT').at(-1).body).image === image, 'Uploaded image URL is included in the subsequent mocked save');

  failSave = true;
  await page.locator('#notes').fill('Synthetic save failure');
  await page.waitForFunction(() => document.querySelector('#saveStatus').textContent.includes('Not saved'));
  check((await page.locator('#saveStatus').textContent()).includes('check connection'), 'Failed save shows the existing connection error');
  failSave = false;
  await page.locator('#notes').fill('Synthetic retry');
  await waitSaved();

  await loadSaved(true);
  await page.waitForFunction(() => document.querySelector('#teamsStatus')?.textContent === 'Teams: copy current');
  check(requests.some(r => r.path.endsWith('/sync') && r.method === 'GET'), 'Ready Teams UI reads mocked sync status');
  await page.getByRole('button', { name: 'Update Teams copy' }).click();
  await page.waitForFunction(() => document.querySelector('#teamsStatus').textContent === 'Teams: copy current');
  check(requests.some(r => r.path.endsWith('/push') && r.method === 'POST'), 'Teams button uses mocked push endpoint');
  failPush = true;
  await page.getByRole('button', { name: 'Update Teams copy' }).click();
  await page.waitForFunction(() => document.querySelector('#teamsStatus').textContent === 'Teams: push failed');
  check(true, 'Teams failure is reflected in status');

  await page.evaluate(() => { window.confirm = () => true; });
  await page.evaluate(() => resetTicket());
  await waitSaved();
  check(await page.locator('#jobName').inputValue() === '' && await page.locator('#matBody tr').count() === 1 && await page.locator('#prodBody tr').count() === 1, 'Confirmed reset clears fields and retains one row per table');
  await loadSaved();
  await page.emulateMedia({ media: 'print' });
  check(await page.locator('.toolbar').isHidden() && await page.locator('#jobNo').isVisible() && await page.locator('#jobNoRight').isVisible(), 'Print hides toolbar and preserves both job numbers');
  await page.pdf({ path: 'output/playwright/saved-demo.pdf', printBackground: true, preferCSSPageSize: true });
  await page.emulateMedia({ media: 'screen' });
  check(errors.length === 0, 'No browser JavaScript errors');
  check(blocked.length === 0, 'No external browser requests attempted; all requests stayed local');
  return { passed: checks.length, checks, mockedApiRequests: requests.length, pageErrors: errors, blockedExternalRequests: blocked };
}
