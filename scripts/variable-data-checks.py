"""Real isolated Variable Data UI/API checks; no production access or writes."""
from pathlib import Path
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback

import httpx
from playwright.sync_api import sync_playwright
from pypdf import PdfReader


REPO = Path(__file__).resolve().parents[1]
OUT = REPO / 'output' / 'variable-data'
OUT.mkdir(parents=True, exist_ok=True)
checks, errors, external, browser_writes = [], [], [], []


def check(value, label):
    assert value, label
    checks.append(label)


def eventually(predicate, label, page):
    for _ in range(180):
        if predicate():
            return
        page.wait_for_timeout(30)
    raise AssertionError(label)


def pdf_text(path):
    return '\n'.join(sheet.extract_text() or '' for sheet in PdfReader(path).pages)


with tempfile.TemporaryDirectory(prefix='jobticket-variable-data-ui-') as directory:
    root = Path(directory)
    for source in (REPO / 'backend').glob('*.py'):
        shutil.copy2(source, root / source.name)
    shutil.copy2(REPO / 'frontend' / 'ticket.html', root / 'ticket.html')
    shutil.copytree(REPO / 'frontend' / 'static', root / 'static')
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    base = 'http://127.0.0.1:' + str(port)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('GRAPH_', 'PUSH_'))}
    env.update(PORT=str(port), PYTHONDONTWRITEBYTECODE='1')
    log = (OUT / 'server.log').open('w')
    server = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1',
         '--port', str(port), '--log-level', 'error'],
        cwd=root, env=env, stdout=log, stderr=log)
    client = httpx.Client(base_url=base, timeout=10, trust_env=False)
    try:
        for _ in range(100):
            try:
                if client.get('/jobticket/health').status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(.05)
        health = client.get('/jobticket/health').json()
        check(health['graph'] is False, 'Disposable backend has Graph disabled')
        api = '/jobticket/api/VAR01'

        def ticket():
            response = client.get(api)
            response.raise_for_status()
            return response.json()

        def state():
            return ticket()['state']

        fixture = {
            'jobName': 'VAR01 synthetic variable data', 'date': '2026-11-02',
            'qty': '7', 'due': '2026-11-09', 'time': '09:45',
            'notes': 'Keep the original production instructions.',
            'materials': ['Acrylic', 'Acrylic'],
            'materialDetails': ['Front layer: polish edges', 'Back layer: second surface'],
            'materialCompleted': [False, True],
            'materialRowIds': ['row-front', 'row-back'],
            'materialFiles': [None, None], 'materialFileBase': {},
            'steps': [{'op': 'Laser cut', 'instr': 'Use approved vector artwork.'}],
            'image': None,
        }
        check(client.put(api, json=fixture).status_code == 200,
              'Synthetic ticket starts with Variable Data omitted')
        original_bytes = b'%PDF-1.4\nSYNTHETIC APPROVED PRODUCTION FILE\n%%EOF'
        response = client.post(api + '/attachments', files={
            'file': ('approved-production.ai', original_bytes, 'application/postscript')})
        response.raise_for_status()
        attachment = response.json()['file']
        fixture['materialFiles'] = [attachment, None]
        fixture['materialFileBase'] = {'row-front': None, 'row-back': None}
        check(client.put(api, json=fixture).status_code == 200,
              'Real production-file fixture is attached before UI changes')
        original_state = state()
        board_before = client.get('/jobticket/corkboard/api').json()

        def unchanged_adjacent(expected):
            return {key: value for key, value in expected.items() if key != 'variableData'} == original_state

        def legacy_payload():
            return {key: value for key, value in state().items()
                    if key not in ('variableData', 'materialRowIds', 'materialFiles')}

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={'width': 1200, 'height': 1100})

            def route_request(route):
                request = route.request
                if not request.url.startswith(base + '/'):
                    external.append(request.url)
                    return route.abort()
                if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                    browser_writes.append({'method': request.method, 'url': request.url,
                                           'state': request.post_data_json})
                return route.continue_()

            context.route('**/*', route_request)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + '/jobticket/', wait_until='networkidle')
            checkbox = page.get_by_role('checkbox', name='Variable Data', exact=True)
            label = page.locator('.variable-data-label')
            check(not checkbox.is_checked() and not label.is_visible(),
                  'Scratch ticket starts with a blank checkbox and no visible label')
            checkbox.press('Space')
            check(checkbox.is_checked() and label.is_visible(),
                  'Keyboard toggles Variable Data on a scratch ticket')
            page.wait_for_timeout(1000)
            checkbox.press('Space')
            page.wait_for_timeout(1000)
            check(not browser_writes and client.get('/jobticket/health').json()['tickets'] == 1,
                  'Scratch toggles issue no API writes and create no ticket')

            page.goto(base + '/jobticket/VAR01', wait_until='networkidle')
            check(not checkbox.is_checked() and not label.is_visible(),
                  'Existing ticket with no saved flag restores an unchecked checkbox')
            geometry = checkbox.evaluate('''input => {
                const heading=input.closest('h2'), node=[...heading.childNodes].find(
                    child=>child.nodeType===Node.TEXT_NODE && child.textContent.includes('Job Information'));
                const range=document.createRange();range.selectNodeContents(node);
                const text=range.getBoundingClientRect(),box=input.getBoundingClientRect();
                return {rightOfHeading:box.left>=text.right-1, besideHeading:Math.abs(
                    (box.top+box.bottom)/2-(text.top+text.bottom)/2)<=5};
            }''')
            check(geometry['rightOfHeading'] and geometry['besideHeading'],
                  'Blank checkbox sits immediately beside and to the right of Job Information')
            page.screenshot(path=str(OUT / 'desktop-unchecked.png'), full_page=True)
            checkbox.press('Space')
            eventually(lambda: state().get('variableData') is True,
                       'Checked boolean was not autosaved', page)
            check(unchanged_adjacent(state()),
                  'Checking preserves every adjacent field and attachment reference')
            style = label.evaluate('node=>({color:getComputedStyle(node).color,weight:getComputedStyle(node).fontWeight})')
            check(label.is_visible() and style == {'color': 'rgb(21, 128, 61)', 'weight': '700'},
                  'Checked label is visible, green and bold')
            page.reload(wait_until='networkidle')
            check(checkbox.is_checked() and label.is_visible() and state()['variableData'] is True,
                  'Exact true boolean restores after reload')

            for width in (1200, 390, 320):
                page.set_viewport_size({'width': width, 'height': 1100})
                page.wait_for_timeout(50)
                fits = checkbox.evaluate('''input => {
                    const heading=input.closest('h2'),control=input.closest('label'),
                        a=heading.getBoundingClientRect(),b=control.getBoundingClientRect();
                    return document.documentElement.scrollWidth<=innerWidth+1 &&
                        heading.scrollWidth<=heading.clientWidth+1 && b.left>=a.left-1 &&
                        b.right<=a.right+1 && b.top>=a.top-1 && b.bottom<=a.bottom+1;
                }''')
                check(fits, 'Checked heading and control fit the ' + str(width) + 'px viewport')
                page.screenshot(path=str(OUT / ('desktop-checked.png' if width == 1200 else 'mobile-' + str(width) + '-checked.png')),
                                full_page=True)
            page.set_viewport_size({'width': 1200, 'height': 1100})
            page.emulate_media(media='print')
            checked_pdf = OUT / 'checked-letter.pdf'
            page.pdf(path=str(checked_pdf), format='Letter', print_background=True)
            check(label.is_visible() and 'Variable Data' in pdf_text(checked_pdf),
                  'Checked print includes the Variable Data label')
            page.emulate_media(media='screen')

            check(client.put(api, json=legacy_payload()).status_code == 200 and state()['variableData'] is True,
                  'Real old-tab API save preserves an omitted true flag')
            before_invalid = ticket()
            check(client.put(api, json=dict(legacy_payload(), variableData='true')).status_code == 400
                  and ticket() == before_invalid,
                  'Invalid nonboolean API value is rejected without writing')

            checkbox.press('Space')
            eventually(lambda: state().get('variableData') is False,
                       'Unchecked boolean was not autosaved', page)
            page.reload(wait_until='networkidle')
            check(not checkbox.is_checked() and not label.is_visible() and state()['variableData'] is False,
                  'Exact false boolean restores after reload and hides the label')
            check(unchanged_adjacent(state()) and client.get(attachment['url']).content == original_bytes,
                  'Unchecking preserves all adjacent data and original attachment bytes')
            page.emulate_media(media='print')
            unchecked_pdf = OUT / 'unchecked-letter.pdf'
            page.pdf(path=str(unchecked_pdf), format='Letter', print_background=True)
            check(not label.is_visible() and 'Variable Data' not in pdf_text(unchecked_pdf),
                  'Unchecked print omits the Variable Data label')
            page.emulate_media(media='screen')
            check(client.put(api, json=legacy_payload()).status_code == 200 and state()['variableData'] is False,
                  'Real old-tab API save preserves an omitted false flag')
            check(len(browser_writes) == 2 and
                  [write['state'].get('variableData') for write in browser_writes] == [True, False] and
                  all(write['method'] == 'PUT' and write['url'] == base + api for write in browser_writes),
                  'Saved UI toggles send only two ticket PUTs with exact booleans')
            check(client.get('/jobticket/corkboard/api').json() == board_before,
                  'Variable Data changes leave corkboard data unchanged')
            check(not errors and not external, 'No browser errors or external requests')
            context.close()
            browser.close()

        report = {'passed': len(checks), 'checks': checks, 'page_errors': errors,
                  'external_requests': external, 'browser_put_values': [
                      write['state'].get('variableData') for write in browser_writes],
                  'scope': 'Real isolated backend, synthetic ticket and attachment; no production calls'}
        (OUT / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report))
    except Exception:
        report = {'passed_before_failure': len(checks), 'checks': checks,
                  'page_errors': errors, 'external_requests': external,
                  'error': traceback.format_exc()}
        (OUT / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report))
        raise
    finally:
        client.close()
        server.terminate()
        try:
            server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
        log.close()
