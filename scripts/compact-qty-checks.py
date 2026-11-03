"""Isolated real API/SQLite/browser checks for compact toolbar and material steppers.

Run with --red to capture the three missing behaviors before implementation.
Every backend, database and uploaded file lives in a disposable directory.
"""
from pathlib import Path
import copy
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import traceback

import httpx
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / 'output' / 'compact-qty'
OUT.mkdir(parents=True, exist_ok=True)
RED = '--red' in sys.argv
checks, errors, external, writes = [], [], [], []
result = {}


def check(value, label):
    assert value, label
    checks.append(label)


def eventually(predicate, label, page):
    for _ in range(250):
        if predicate():
            return
        page.wait_for_timeout(40)
    raise AssertionError(label)


with tempfile.TemporaryDirectory(prefix='jobticket-compact-qty-') as directory:
    root = Path(directory)
    for source in (REPO / 'backend').glob('*.py'):
        shutil.copy2(source, root / source.name)
    shutil.copy2(REPO / 'frontend' / 'ticket.html', root / 'ticket.html')
    shutil.copytree(REPO / 'frontend' / 'static', root / 'static')
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    base = f'http://127.0.0.1:{port}'
    api = '/jobticket/api/COMPACT01'
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('GRAPH_', 'PUSH_'))}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    log = (OUT / ('red-server.log' if RED else 'server.log')).open('w')
    server = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1',
         '--port', str(port), '--log-level', 'error'],
        cwd=root, env=env, stdout=log, stderr=log)
    client = httpx.Client(base_url=base, timeout=10, trust_env=False)

    def ticket():
        response = client.get(api)
        response.raise_for_status()
        return response.json()

    def state():
        return ticket()['state']

    def db_snapshot():
        with sqlite3.connect(root / 'tickets.db') as connection:
            return connection.execute(
                'SELECT job_id, data, updated_at FROM tickets ORDER BY job_id').fetchall()

    try:
        for _ in range(100):
            try:
                if client.get('/jobticket/health').status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(.05)
        check(client.get('/jobticket/health').json()['graph'] is False,
              'Disposable backend runs with Graph disabled')
        fixture = {
            'jobName': 'COMPACT01 café 🐂 sample', 'date': '2026-11-02',
            'qty': '7', 'due': '2026-11-09', 'time': '09:45',
            'notes': 'Approved notes café 🐂', 'variableData': True,
            'materials': ['Acrylic', 'Acrylic'],
            'materialDetails': ['Front layer', 'Back layer'],
            'materialCompleted': [False, True],
            'materialRowIds': ['row-first', 'row-second'],
            'materialQuantities': ['', '12'],
            'materialFiles': [None, None], 'materialFileBase': {},
            'steps': [{'op': 'Laser cut', 'instr': 'Approved vector artwork.'}],
            'productionRowIds': ['production-first'], 'image': None,
            'richText': {'version': 1, 'fields': {
                'notes': [{'text': 'Approved', 'bold': True},
                          {'text': ' notes café 🐂'}]}}
        }
        check(client.put(api, json=fixture).status_code == 200,
              'Synthetic duplicate-row ticket includes formatting and Variable Data')
        original = b'%PDF-1.4\nSYNTHETIC APPROVED ORIGINAL BYTES\n%%EOF'
        upload = client.post(api + '/attachments', files={
            'file': ('approved.ai', original, 'application/postscript')})
        upload.raise_for_status()
        attachment = upload.json()['file']
        fixture = state()
        fixture.update(materialFiles=[attachment, None],
                       materialFileBase={'row-first': None, 'row-second': None},
                       richTextBase=fixture['richText'])
        check(client.put(api, json=fixture).status_code == 200,
              'Real attachment fixture stored in disposable backend')
        baseline = copy.deepcopy(state())
        board = client.get('/jobticket/corkboard/api').json()

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={'width': 1200, 'height': 1100})

            def route_request(route):
                request = route.request
                if not request.url.startswith(base + '/'):
                    external.append(request.url)
                    return route.abort()
                if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                    writes.append({'method': request.method, 'url': request.url})
                return route.continue_()

            context.route('**/*', route_request)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + '/jobticket/COMPACT01', wait_until='networkidle')
            page.wait_for_timeout(1000)
            check(not writes and state() == baseline,
                  'Opening saved ticket issues no API writes or state changes')
            headers = page.locator('table.materials-data thead th').all_text_contents()
            geometry = page.locator('.toolbar').evaluate('''toolbar => {
                const print=toolbar.querySelector('button'),saved=document.querySelector('#saveStatus');
                const a=print.getBoundingClientRect(),b=saved.getBoundingClientRect();
                return {height:toolbar.getBoundingClientRect().height,
                    printTop:a.top,printBottom:a.bottom,savedTop:b.top,savedBottom:b.bottom,
                    sameRow:Math.max(a.top,b.top)<Math.min(a.bottom,b.bottom)};
            }''')
            up = page.get_by_role('button', name='Increase material quantity 1', exact=True)
            down = page.get_by_role('button', name='Decrease material quantity 1', exact=True)
            gaps = {
                'qty_first': headers[:2] == ['QTY', 'Material'],
                'toolbar_compact_same_row': geometry['height'] <= 85 and geometry['sameRow'],
                'visible_steppers': up.count() == 1 and down.count() == 1
                    and up.is_visible() and down.is_visible(),
            }
            if RED:
                page.screenshot(path=str(OUT / 'red-desktop.png'), full_page=True)
                result = {'expected_red': not all(gaps.values()), 'gaps': gaps,
                          'headers': headers, 'toolbar': geometry, 'checks': checks,
                          'page_errors': errors, 'external': external,
                          'scope': 'Disposable localhost backend, SQLite and synthetic attachment only'}
                assert not any(gaps.values()), 'Expected all three pre-implementation gaps'
                print(json.dumps(result))
                browser.close()
            else:
                check(gaps['qty_first'], 'QTY is first, immediately left of Material')
                check(gaps['toolbar_compact_same_row'],
                      'Print and Saved share one row; desktop toolbar <=85px ' + str(geometry))
                check(gaps['visible_steppers'], 'Row one has visible accessible Up/Down controls')
                check(page.get_by_role('button', name='Increase material quantity 2', exact=True).is_visible()
                      and page.get_by_role('button', name='Decrease material quantity 2', exact=True).is_visible(),
                      'Each material row has individually labelled visible Up/Down controls')
                quantities = page.locator('.material-quantity')

                def saved_quantities(expected):
                    eventually(lambda: state()['materialQuantities'] == expected,
                               'Quantities did not autosave: ' + repr(expected), page)
                    eventually(lambda: page.locator('#saveStatus').inner_text().startswith('Saved'),
                               'Saved acknowledgement did not settle', page)

                check(quantities.nth(0).input_value() == '', 'Blank material QTY remains blank on load')
                up.click()
                check(quantities.nth(0).input_value() == '1', 'Up converts blank to 1')
                saved_quantities(['1', '12'])
                check(state()['materialQuantities'][1] == '12', 'Stepping first row leaves second row independent')
                down.click()
                check(quantities.nth(0).input_value() == '0', 'Down decrements 1 to 0')
                saved_quantities(['0', '12'])

                def unchanged_action(action, label):
                    page.wait_for_timeout(400)
                    before_db, before_writes = db_snapshot(), len(writes)
                    action()
                    page.wait_for_timeout(1000)
                    check(db_snapshot() == before_db and len(writes) == before_writes, label)

                unchanged_action(down.click, 'Down at zero neither saves nor revises SQLite')
                quantities.nth(0).fill('')
                saved_quantities(['', '12'])
                down.click()
                check(quantities.nth(0).input_value() == '0', 'Down converts blank to 0 without going negative')
                saved_quantities(['0', '12'])
                quantities.nth(0).press('ArrowUp')
                check(quantities.nth(0).input_value() == '1', 'ArrowUp increments material quantity')
                saved_quantities(['1', '12'])
                quantities.nth(0).press('ArrowDown')
                check(quantities.nth(0).input_value() == '0', 'ArrowDown decrements material quantity')
                saved_quantities(['0', '12'])
                unchanged_action(lambda: quantities.nth(0).press('ArrowDown'),
                                 'ArrowDown at zero does not issue a save')
                quantities.nth(0).fill('99')
                saved_quantities(['99', '12'])
                digits_geometry = quantities.nth(0).evaluate('''input => {
                    const box=input.getBoundingClientRect(),cell=input.closest('td').getBoundingClientRect(),
                        up=input.closest('td').querySelector('.quantity-step-up').getBoundingClientRect(),
                        down=input.closest('td').querySelector('.quantity-step-down').getBoundingClientRect(),
                        s=getComputedStyle(input),canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');
                    ctx.font=s.font;const available=input.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight);
                    return {available,required:ctx.measureText('99').width,
                        arrowsInside:up.left>=cell.left&&up.right<=cell.right+1&&down.left>=cell.left&&down.right<=cell.right+1,
                        separate:Math.min(up.left,down.left)>=box.right-1};
                }''')
                check(digits_geometry['available'] >= digits_geometry['required']
                      and digits_geometry['arrowsInside'] and digits_geometry['separate'],
                      'Two digits fit visibly beside nonoverlapping arrows ' + str(digits_geometry))
                up.click()
                check(quantities.nth(0).input_value() == '100', 'Up allows 99 to become 100')
                saved_quantities(['100', '12'])
                quantities.nth(0).fill('999999998')
                saved_quantities(['999999998', '12'])
                up.click()
                check(quantities.nth(0).input_value() == '999999999', 'Up reaches the nine-digit maximum')
                saved_quantities(['999999999', '12'])
                unchanged_action(up.click, 'Up at nine-digit maximum does not save or overflow')
                unchanged_action(lambda: quantities.nth(0).press('ArrowUp'),
                                 'ArrowUp at nine-digit maximum does not save or overflow')
                quantities.nth(0).fill('1234567890')
                check(quantities.nth(0).input_value() == '999999999'
                      and quantities.nth(0).get_attribute('aria-invalid') == 'true',
                      'Ten-digit direct edits retain the prior valid quantity')
                down.click()
                check(quantities.nth(0).input_value() == '999999998'
                      and quantities.nth(0).get_attribute('aria-invalid') is None,
                      'A valid step clears invalid-input feedback')
                saved_quantities(['999999998', '12'])
                quantities.nth(0).fill('23')
                saved_quantities(['23', '12'])
                page.get_by_role('button', name='Increase material quantity 2', exact=True).click()
                saved_quantities(['23', '13'])
                check(quantities.nth(0).input_value() == '23', 'Stepping second row leaves first row independent')
                adjacent = state()
                check(all(adjacent[key] == baseline[key] for key in baseline if key != 'materialQuantities'),
                      'Quantity changes preserve formatting, text, completion, Variable Data and attachment references')
                check(client.get(attachment['url']).content == original,
                      'Quantity changes preserve uploaded attachment bytes exactly')
                before_reload = copy.deepcopy(state())
                before_writes = len(writes)
                page.reload(wait_until='networkidle')
                page.wait_for_timeout(1000)
                check(state() == before_reload and len(writes) == before_writes
                      and [quantities.nth(i).input_value() for i in range(2)] == ['23', '13'],
                      'Reload restores saved quantities and formatted state without saving')
                check(page.get_by_role('checkbox', name='Variable Data', exact=True).is_checked()
                      and page.locator('.variable-data-label').is_visible(),
                      'Variable Data remains visibly checked after quantity changes')
                check(page.locator('.rich-editor[data-rich-key="notes"] span').first.evaluate(
                    'el=>parseInt(getComputedStyle(el).fontWeight,10)>=700'),
                      'Approved bold formatting remains rendered after reload')
                page.screenshot(path=str(OUT / 'desktop.png'), full_page=True)

                for width in (390, 320):
                    page.set_viewport_size({'width': width, 'height': 1100})
                    check(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),
                          'Ticket and toolbar fit viewport at ' + str(width))
                    usable = page.locator('.rich-editor[data-rich-key="material:row-second:details"]').evaluate('''e=>{
                        const s=getComputedStyle(e);return e.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)}''')
                    check(usable >= 60, 'Material Details retain >=60px usable text width at '
                          + str(width) + ': ' + str(usable))
                    check(up.is_visible() and down.is_visible(),
                          'Visible quantity arrows survive narrow width ' + str(width))
                    done_fits=page.locator('.material-completion-heading').evaluate('''e=>{const r=document.createRange();r.selectNodeContents(e);const s=getComputedStyle(e);return r.getBoundingClientRect().width<=e.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)}''')
                    check(done_fits,'Done heading is fully readable at '+str(width))
                    page.screenshot(path=str(OUT / f'mobile-{width}.png'), full_page=True)
                page.set_viewport_size({'width': 1200, 'height': 1100})
                page.emulate_media(media='print')
                check(not up.is_visible() and not down.is_visible()
                      and not page.get_by_role('button', name='Bold', exact=True).is_visible()
                      and not page.locator('.toolbar').is_visible(),
                      'Print hides quantity buttons and every toolbar control')
                print_headers = page.locator('table.materials-data th:visible').all_text_contents()
                check(print_headers[:2] == ['QTY', 'Material'], 'Printed QTY remains first and left of Material')
                row_print = page.locator('#matBody tr').first.evaluate('''row=>{
                    const qty=row.querySelector('.material-quantity'),label=row.querySelector('.material-quantity-print');
                    return {visible:[qty,label].filter(el=>getComputedStyle(el).display!=='none').length,
                        text:label.textContent};}''')
                check(row_print == {'visible': 1, 'text': '23'},
                      'Print renders exactly one quantity per row')
                page.screenshot(path=str(OUT / 'print.png'), full_page=True)
                pdf = OUT / 'compact-ticket.pdf'
                page.pdf(path=str(pdf), format='Letter', print_background=True)
                pdf_text = '\n'.join(sheet.extract_text() or '' for sheet in PdfReader(pdf).pages)
                check('23' in pdf_text and '13' in pdf_text and 'Variable Data' in pdf_text
                      and 'Approved' in pdf_text and 'approved.ai' in pdf_text,
                      'Real PDF retains quantities, Variable Data, formatted prose and attachment name')
                page.emulate_media(media='screen')

                # Duplicate-name row deletion must preserve the surviving row's own QTY and controls.
                page.locator('#matBody tr').first.locator('.row-delete').click()
                saved_quantities(['13'])
                check(state()['materialRowIds'] == ['row-second']
                      and state()['materialCompleted'] == [True],
                      'Deleting first duplicate keeps quantity and completion with surviving stable row')
                check(page.get_by_role('button', name='Increase material quantity 1', exact=True).is_visible()
                      and page.get_by_role('button', name='Decrease material quantity 1', exact=True).is_visible()
                      and page.get_by_role('button', name='Increase material quantity 2', exact=True).count() == 0,
                      'Deleting a row renumbers both accessible stepper labels')
                page.get_by_role('button', name='Increase material quantity 1', exact=True).click()
                saved_quantities(['14'])
                check(state()['materialRowIds'] == ['row-second'], 'Renumbered row steppers change surviving row only')
                detail = page.locator('.rich-editor[data-rich-key="material:row-second:details"]')
                detail.click()
                detail.press('End')
                detail.press('Enter')
                check(page.locator('#matBody tr').count() == 2
                      and page.get_by_role('button', name='Increase material quantity 2', exact=True).is_visible(),
                      'New material row gets its own visible accessible stepper controls')
                saved_quantities(['14', ''])
                page.get_by_role('button', name='Decrease material quantity 2', exact=True).click()
                saved_quantities(['14', '0'])
                page.locator('#matBody tr').last.locator('.row-delete').click()
                saved_quantities(['14'])
                check(client.get(attachment['url']).content == original,
                      'Deleting the associated row does not modify original uploaded bytes')
                check(client.get('/jobticket/corkboard/api').json() == board,
                      'Ticket editing leaves corkboard records unchanged')

                # Scratch tickets must never turn these reversible edits into persisted records.
                before_scratch_db, before_scratch_writes = db_snapshot(), len(writes)
                page.goto(base + '/jobticket/', wait_until='networkidle')
                row_heights = page.evaluate('''()=>({
                    material:document.querySelector('#matBody tr').getBoundingClientRect().height,
                    production:document.querySelector('#prodBody tr').getBoundingClientRect().height})''')
                check(row_heights['material'] <= 22
                      and abs(row_heights['material'] - row_heights['production']) <= 1,
                      'Steppers preserve compact matching material/production row height ' + str(row_heights))
                page.get_by_role('button', name='Increase material quantity 1', exact=True).click()
                page.locator('.material-quantity').first.press('ArrowUp')
                check(page.locator('.material-quantity').first.input_value() == '2',
                      'Scratch ticket supports visible and keyboard stepping')
                page.locator('.rich-editor[data-rich-key="notes"]').fill('Scratch prose')
                page.wait_for_timeout(1100)
                check(db_snapshot() == before_scratch_db and len(writes) == before_scratch_writes,
                      'Opening and editing scratch ticket creates no save or SQLite write')
                check(not errors and not external, 'No browser errors or nonlocal requests')
                result = {'passed': len(checks), 'checks': checks, 'toolbar': geometry,
                          'row_heights': row_heights,
                          'scope': 'Disposable localhost backend, SQLite and synthetic attachment only'}
                print(json.dumps(result))
                browser.close()
    except Exception:
        result = dict(result, passed_before_failure=len(checks), checks=checks,
                      error=traceback.format_exc(), page_errors=errors, external=external)
        raise
    finally:
        (OUT / ('red-results.json' if RED else 'results.json')).write_text(
            json.dumps(result, indent=2) + '\n')
        client.close()
        server.terminate()
        server.wait(timeout=8)
        log.close()
