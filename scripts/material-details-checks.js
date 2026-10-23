// Run with Playwright CLI run-code --filename=scripts/material-details-checks.js.
// Fresh session; preview.py --port 18765. Real UI, synthetic local HTTP only.
async (page) => {
  const origin = 'http://127.0.0.1:18765';
  const results = [], pageErrors = [], externalRequests = [];
  const assert = (value, message) => { if (!value) throw new Error(message); };
  await page.clock.install({ time: new Date('2026-10-21T12:00:00Z') });
  await page.clock.pauseAt(new Date('2026-10-21T12:01:00Z'));

  async function run(name, fixture, test, scratch = false) {
    const p = await page.context().newPage();
    p.setDefaultTimeout(3000);
    let stored = fixture, holdSave = false;
    const saves = [], pushes = [];
    const advance = async ms => { await p.clock.runFor(ms); await p.waitForTimeout(30); };
    const eventually = async (predicate, message) => {
      for (let i = 0; i < 100; i++) {
        if (await predicate()) return;
        await p.waitForTimeout(10);
      }
      throw new Error(message);
    };
    const reply = async index => {
      stored = saves[index].state;
      await saves[index].route.fulfill({ json: { ok: true, savedAt: 1 } });
      await p.waitForTimeout(30);
    };
    p.on('pageerror', error => pageErrors.push({ name, message: error.message }));
    await p.route('**/*', async route => {
      const req = route.request(), url = new URL(req.url());
      if (url.origin !== origin) { externalRequests.push(req.url()); return route.abort('blockedbyclient'); }
      if (url.pathname === '/jobticket/DEMO01') {
        const response = await route.fetch();
        const body = (await response.text()).replace(/window\.__TICKET__ = (.*?);<\/script>/, (_, payload) => {
          const boot = JSON.parse(payload);
          Object.assign(boot.state, stored);
          return 'window.__TICKET__ = ' + JSON.stringify(boot).replace(/</g, '\\u003c') + ';</script>';
        });
        return route.fulfill({ response, body });
      }
      if (url.pathname === '/jobticket/api/DEMO01' && req.method() === 'PUT') {
        saves.push({ route, state: req.postDataJSON() });
        if (!holdSave) return reply(saves.length - 1);
        return;
      }
      if (url.pathname.endsWith('/sync')) return route.fulfill({ json: { error: '', stale: false, pushedAt: 1 } });
      if (url.pathname.endsWith('/push')) { pushes.push(JSON.parse(JSON.stringify(stored))); return route.fulfill({ json: { ok: true } }); }
      if (url.pathname.startsWith('/jobticket/api/')) return route.abort('blockedbyclient');
      return route.continue();
    });
    try {
      await p.setViewportSize({ width: 1200, height: 1300 });
      await p.goto(origin + (scratch ? '/jobticket/' : '/jobticket/DEMO01?teams=1'));
      await advance(1);
      assert(await p.locator('#matBody textarea.material-details').count() > 0, 'Material details control is missing from materials rows');
      await test({ p, saves, pushes, advance, eventually, reply, holdSave: () => { holdSave = true; }, stored: () => stored });
      results.push({ name, passed: true });
    } catch (error) {
      results.push({ name, passed: false, error: error.message });
    } finally { await p.unrouteAll({ behavior: 'wait' }); await p.close(); }
  }

  await run('Legacy tickets retain materials with blank adjacent details', { materials: ['Clear acrylic', 'White acrylic'] }, async t => {
    assert(JSON.stringify(await t.p.locator('#matBody input[data-row-input="mat"]').evaluateAll(nodes => nodes.map(n => n.value))) === '["Clear acrylic","White acrylic"]', 'Legacy material names changed');
    assert(JSON.stringify(await t.p.locator('.material-details').evaluateAll(nodes => nodes.map(n => n.value))) === '["",""]', 'Missing details were not restored as blank');
    assert(await t.p.getByRole('columnheader', { name: 'Material details', exact: true }).count() === 1, 'Separate Material details heading missing');
    assert(await t.p.getByRole('columnheader', { name: '#', exact: true }).count() === 0 && await t.p.locator('#matBody .row-num').count() === 0, 'Materials numbering column must be absent');
    assert(await t.p.locator('#prodBody .row-num').first().textContent() === '1', 'Production step numbering must remain');
    const widths = await t.p.locator('#matBody tr').first().evaluate(row => [row.querySelector('[data-row-input="mat"]').closest('td'), row.querySelector('.material-details-cell')].map(cell => cell.getBoundingClientRect().width));
    assert(widths[0] / (widths[0] + widths[1]) >= .25 && widths[0] / (widths[0] + widths[1]) <= .31, 'Material column should use about 28 percent of editable width');
    await t.advance(1000);
    assert(t.saves.length === 0, 'Restoring legacy data unexpectedly saved');
  });

  await run('Details serialize, restore, wrap and stay aligned when rows change', { materials: ['Clear acrylic'] }, async t => {
    const details = 'Cut to 12 × 24 in\nPolish the edges';
    await t.p.locator('.material-details').first().fill(details);
    await t.p.locator('.material-details').first().press('Shift+Enter');
    assert(await t.p.locator('#matBody tr').count() === 1 && (await t.p.locator('.material-details').first().inputValue()).endsWith('\n'), 'Shift+Enter did not retain multiline details');
    const preservedDetails = await t.p.locator('.material-details').first().inputValue();
    await t.p.locator('.material-details').first().press('Enter');
    assert(await t.p.locator('#matBody tr').count() === 2 && await t.p.getByLabel('Material 2', { exact: true }).count() === 1, 'Enter in details did not add the next material row');
    assert(await t.p.locator('.material-details').first().inputValue() === preservedDetails, 'Enter changed the existing details');
    assert(await t.p.locator('#matBody input[data-row-input="mat"]').nth(1).evaluate(n => n === document.activeElement), 'Enter did not focus the next Material field');
    await t.p.locator('#matBody input[data-row-input="mat"]').nth(1).fill('White acrylic');
    await t.p.locator('.material-details').nth(1).fill('3 mm, matte finish');
    await t.advance(800);
    await t.eventually(() => t.saves.length > 0, 'Details edits were not saved');
    assert(t.stored().materialDetails[0].startsWith(details) && t.stored().materialDetails[1] === '3 mm, matte finish', 'PUT lost material details');
    assert(t.stored().materials[0] === 'Clear acrylic', 'Existing materials array was replaced or corrupted');
    await t.p.reload();
    await t.advance(1);
    assert((await t.p.locator('.material-details').first().inputValue()).startsWith(details), 'Saved details were not restored');
    await t.p.locator('#matBody .row-delete').first().evaluate(b => b.click());
    await t.advance(800);
    await t.eventually(() => t.stored().materials.length === 1, 'Row deletion was not saved');
    assert(t.stored().materials[0] === 'White acrylic' && t.stored().materialDetails[0] === '3 mm, matte finish', 'Row deletion misaligned details');
    assert(await t.p.getByRole('textbox', { name: 'Material details 1', exact: true }).count() === 1, 'Row accessibility labels were not renumbered');
  });

  await run('Reset cancellation preserves details; confirmed Reset clears them', { materials: ['Clear acrylic'], materialDetails: ['Keep this detail'] }, async t => {
    await t.p.evaluate(() => { window.confirm = () => false; });
    await t.p.getByRole('button', { name: 'Reset', exact: false }).evaluate(b => b.click());
    await t.advance(1000);
    assert(t.saves.length === 0 && await t.p.locator('.material-details').inputValue() === 'Keep this detail', 'Cancelled Reset changed details or saved');
    await t.p.evaluate(() => { window.confirm = () => true; });
    await t.p.getByRole('button', { name: 'Reset', exact: false }).evaluate(b => b.click());
    await t.advance(800);
    await t.eventually(() => t.saves.length === 1, 'Confirmed Reset did not save');
    assert(JSON.stringify(t.stored().materialDetails) === '[""]' && JSON.stringify(t.stored().materials) === '[""]', 'Confirmed Reset retained material values');
  });

  await run('Teams push includes details only after their save succeeds', { materials: ['Clear acrylic'], materialDetails: ['Old detail'] }, async t => {
    t.holdSave();
    await t.p.locator('.material-details').fill('New detail for the snapshot');
    await t.p.getByRole('button', { name: 'Update Teams copy' }).evaluate(b => b.click());
    await t.eventually(() => t.saves.length === 1, 'Teams did not save details');
    await t.advance(1500);
    assert(t.pushes.length === 0, 'Teams pushed before details finished saving');
    await t.reply(0);
    await t.eventually(() => t.pushes.length === 1, 'Teams did not push after save');
    assert(t.pushes[0].materialDetails[0] === 'New detail for the snapshot', 'Teams snapshot state omitted details');
  });

  const longDetail = 'Cut to size and polish edges. '.repeat(15) + '\nLiteral <b>not HTML</b> ' + 'X'.repeat(100);
  await run('Narrow screens and print keep both columns readable without clipping', { materials: ['Long material description for print'], materialDetails: [longDetail] }, async t => {
    await t.p.evaluate(() => document.fonts.ready);
    for (const width of [390, 320]) {
      await t.p.setViewportSize({ width, height: 1000 });
      await t.advance(20);
      const layout = await t.p.evaluate(() => {
        const row = document.querySelector('#matBody tr'), detail = row.querySelector('textarea');
        return { overflow: document.documentElement.scrollWidth > window.innerWidth + 1, columns: [row.querySelector('[data-row-input="mat"]').closest('td'), row.querySelector('.material-details-cell')].map(c => { const r = c.getBoundingClientRect(); return { x: r.x, right: r.right, width: r.width }; }), clipped: detail.scrollHeight > detail.clientHeight + 2 };
      });
      assert(!layout.overflow && layout.columns[1].right <= width, 'Material row overflows the narrow viewport');
      assert(layout.columns[0].width < layout.columns[1].width * .5 && layout.columns[0].right <= layout.columns[1].x + 1, 'Narrow material columns overlap or lose the narrower material split');
      assert(!layout.clipped, 'Wrapped material details are clipped on screen');
    }
    await t.p.screenshot({ path: 'output/playwright/materials-mobile.png', fullPage: true });
    await t.p.setViewportSize({ width: 1200, height: 1300 });
    await t.advance(20);
    await t.p.screenshot({ path: 'output/playwright/materials-desktop.png', fullPage: true });
    await t.p.emulateMedia({ media: 'print' });
    await t.advance(20);
    const printed = t.p.locator('.material-details-print').first();
    assert(await printed.isVisible() && await printed.textContent() === longDetail, 'Print does not show complete literal details');
    assert(await printed.locator('b').count() === 0, 'Details were interpreted as HTML');
    assert(await t.p.locator('.material-details').first().isHidden(), 'Print still uses a clipping textarea');
    assert(await t.p.locator('.material-name-print').textContent() === 'Long material description for print', 'Print lost the material name');
    const printLayout = await printed.evaluate(node => ({ clipped: node.scrollWidth > node.clientWidth + 1, widths: [node.closest('tr').querySelector('[data-row-input="mat"]').closest('td'), node.closest('tr').querySelector('.material-details-cell')].map(cell => cell.getBoundingClientRect().width) }));
    assert(!printLayout.clipped && printLayout.widths[0] < printLayout.widths[1] * .5, 'Print text overflows or material column is not narrower');
    await t.p.screenshot({ path: 'output/playwright/materials-print.png', fullPage: true });
    await t.p.pdf({ path: 'output/playwright/materials-print.pdf', printBackground: true, preferCSSPageSize: true });
    await t.p.emulateMedia({ media: 'screen' });
    await t.advance(20);
    assert(await t.p.locator('.material-details').evaluate(node => node.scrollHeight <= node.clientHeight + 2), 'Returning from print clipped the details');
  });

  await run('Scratch details remain editable and unsaved', {}, async t => {
    await t.p.locator('.material-details').fill('Scratch material note');
    await t.advance(1000);
    assert(t.saves.length === 0 && t.pushes.length === 0, 'Scratch detail edit called an API');
    assert(await t.p.locator('#saveStatus').textContent() === 'Scratch ticket · not saved', 'Scratch status changed');
  }, true);

  await run('Completion toggles highlight, saves, restores and stays aligned', { materials: ['Clear acrylic', 'White acrylic'], materialDetails: ['First detail', 'Second detail'] }, async t => {
    const first = t.p.getByRole('checkbox', { name: 'Completed 1', exact: true });
    assert(await first.count() === 1 && !(await first.isChecked()), 'Legacy row must start unchecked');
    const ordinary = await t.p.locator('#matBody tr').first().evaluate(r => getComputedStyle(r.querySelector('[data-row-input="mat"]').closest('td')).backgroundColor);
    await first.check();
    assert(await t.p.locator('#matBody tr').first().evaluate(r => r.classList.contains('material-is-completed') && Array.from(r.cells).every(c => getComputedStyle(c).backgroundColor === 'rgb(240, 253, 244)')), 'Whole completed row must be very light green');
    await t.advance(800);
    await t.eventually(() => t.stored().materialCompleted?.[0] === true, 'Checked state was not saved');
    assert(JSON.stringify(t.stored().materialCompleted) === '[true,false]', 'Completion state is not aligned');
    await t.p.reload(); await t.advance(1);
    assert(await first.isChecked(), 'Reload lost completion');
    await first.uncheck(); await t.advance(800);
    await t.eventually(() => t.stored().materialCompleted[0] === false, 'Uncheck was not saved');
    assert(await t.p.locator('#matBody tr').first().evaluate(r => getComputedStyle(r.querySelector('[data-row-input="mat"]').closest('td')).backgroundColor) === ordinary, 'Uncheck did not restore background');
    await t.p.getByRole('checkbox', { name: 'Completed 2', exact: true }).check();
    await t.p.locator('#matBody .row-delete').first().click(); await t.advance(800);
    await t.eventually(() => t.stored().materials.length === 1, 'Deletion did not save');
    assert(t.stored().materials[0] === 'White acrylic' && t.stored().materialCompleted[0] === true, 'Deletion misaligned completion');
    assert(await t.p.getByRole('checkbox', { name: 'Completed 1', exact: true }).isChecked(), 'Completion accessibility label was not renumbered');
    await t.p.locator('#matBody input[data-row-input="mat"]').first().press('Enter'); await t.advance(800);
    await t.eventually(() => t.stored().materialCompleted.length === 2, 'Addition did not save');
    assert(t.stored().materialCompleted[1] === false, 'New row should be unchecked');
  });

  await run('Reset cancellation keeps completion and confirmed reset clears it', { materials: ['Acrylic'], materialCompleted: [true] }, async t => {
    await t.p.evaluate(() => { window.confirm = () => false; });
    await t.p.getByRole('button', { name: 'Reset', exact: false }).click(); await t.advance(1000);
    assert(t.saves.length === 0 && await t.p.getByRole('checkbox', { name: 'Completed 1', exact: true }).isChecked(), 'Cancelled reset changed completion');
    await t.p.evaluate(() => { window.confirm = () => true; });
    await t.p.getByRole('button', { name: 'Reset', exact: false }).click(); await t.advance(800);
    await t.eventually(() => t.saves.length > 0, 'Reset did not save');
    assert(JSON.stringify(t.stored().materialCompleted) === '[false]', 'Reset did not clear completion');
  });

  await run('Completion remains visible at the far right on narrow screens and print', { materials: ['Acrylic', 'White acrylic'], materialDetails: ['Finished material', 'Not finished'], materialCompleted: [true, false] }, async t => {
    for (const width of [1200, 390, 320]) {
      await t.p.setViewportSize({ width, height: 1000 }); await t.advance(20);
      const layout = await t.p.locator('#matBody tr').first().evaluate(r => {
        const box = r.querySelector('.material-completed').getBoundingClientRect(), detail = r.querySelector('.material-details-cell').getBoundingClientRect();
        return { overflow: document.documentElement.scrollWidth > innerWidth + 1, x: box.x, right: box.right, width: box.width, detailRight: detail.right, last: r.lastElementChild.contains(r.querySelector('.material-completed')) };
      });
      assert(!layout.overflow && layout.last && layout.x >= layout.detailRight && layout.right <= width && layout.width >= 16, 'Completion control is not usable at the far right');
    }
    await t.p.setViewportSize({ width: 1200, height: 1300 }); await t.advance(20);
    await t.p.screenshot({ path: 'output/playwright/completed-screen.png', fullPage: true });
    await t.p.emulateMedia({ media: 'print' }); await t.advance(20);
    assert(await t.p.locator('.material-completion-print').first().isVisible(), 'Print completion indicator is missing');
    assert(await t.p.locator('.material-completion-print').first().textContent() === '[x]' && await t.p.locator('.material-completion-print').nth(1).textContent() === '[ ]', 'Printed checked state relies on color only');
    assert(await t.p.locator('#matBody tr').first().evaluate(r => getComputedStyle(r.querySelector('.material-details-cell')).backgroundColor) === 'rgb(240, 253, 244)', 'Print lost completed row highlight');
    await t.p.screenshot({ path: 'output/playwright/completed-print.png', fullPage: true });
    await t.p.pdf({ path: 'output/playwright/completed-print.pdf', printBackground: true, preferCSSPageSize: true });
  });

  await run('Short material rows match production, including after completion and wrapping', {}, async t => {
    await t.p.evaluate(() => document.fonts.ready);
    const height = locator => locator.evaluate(n => n.getBoundingClientRect().height);
    const materialRow = t.p.locator('#matBody tr').first();
    const productionRow = t.p.locator('#prodBody tr').first();
    for (const width of [1200, 390, 320]) {
      await t.p.setViewportSize({ width, height: 1000 }); await t.advance(20);
      for (const completed of [false, true]) {
        await t.p.locator('.material-completed').first().setChecked(completed);
        assert(Math.abs(await height(materialRow) - await height(productionRow)) <= 1, 'Short material row is taller than production at width ' + width);
      }
    }
    await t.p.setViewportSize({ width: 1200, height: 1300 }); await t.advance(20);
    await t.p.locator('.material-details').first().fill('Long wrapping details. '.repeat(30));
    assert(await height(materialRow) > await height(productionRow), 'Long details no longer expand');
    await t.p.locator('.material-details').first().fill('Short detail');
    assert(Math.abs(await height(materialRow) - await height(productionRow)) <= 1, 'Short details did not shrink back to production height');
    await t.p.locator('#prodBody textarea').fill('Cut');
    await t.p.locator('#prodBody textarea').press('Enter');
    assert(await t.p.locator('#prodBody tr').count() === 1 && await t.p.locator('#prodBody textarea').inputValue() === 'Cut\n', 'Production instructions lost Enter newlines');
    await t.p.screenshot({ path: 'output/playwright/compact-materials.png', fullPage: true });
  }, true);

  await run('Scratch completion is local and unsaved', {}, async t => {
    await t.p.getByRole('checkbox', { name: 'Completed 1', exact: true }).check(); await t.advance(1000);
    assert(t.saves.length === 0 && t.pushes.length === 0, 'Scratch completion made an API call');
  }, true);

  await page.clock.resume();
  return { passed: results.filter(r => r.passed).length, failed: results.filter(r => !r.passed).length, results, pageErrors, externalRequests };
}
