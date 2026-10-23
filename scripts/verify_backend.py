"""Isolated real API/SQLite/browser/PDF checks; all Graph transport is intercepted.

Requires FastAPI, uvicorn, python-multipart, httpx, pypdf and Playwright/Chromium.
Set PLAYWRIGHT_BROWSERS_PATH if Chromium lives outside its default cache.
"""
from pathlib import Path
import hashlib, importlib, io, json, os, shutil, socket, sys, tempfile, threading, time
from unittest.mock import patch
import httpx
import uvicorn
from pypdf import PdfReader
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'output' / 'backend'
ROOT.mkdir(parents=True, exist_ok=True)
PORT = 18766
BASE = f'http://127.0.0.1:{PORT}'
for key in list(os.environ):
    if key.startswith(('GRAPH_', 'PUSH_')):
        del os.environ[key]
os.environ['PORT'] = str(PORT)
original_connect = socket.socket.connect
def local_connect(sock, address):
    if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1', 'localhost'):
        raise RuntimeError('Non-local network blocked: ' + str(address[0]))
    return original_connect(sock, address)
socket.socket.connect = local_connect
checks = []
def check(value, name):
    assert value, name
    checks.append(name)

isolation = Path(tempfile.mkdtemp(prefix='backend-', dir=ROOT))
for name in ['app.py', 'graph.py', 'pdf.py']:
    shutil.copyfile(REPO / 'backend' / name, isolation / name)
shutil.copyfile(REPO / 'frontend/ticket.html', isolation / 'ticket.html')
shutil.copytree(REPO / 'frontend/static', isolation / 'static')
sys.path.insert(0, str(isolation))
original_start = threading.Thread.start
def controlled_start(thread):
    if getattr(getattr(thread, '_target', None), '__name__', '') != 'sync_worker':
        original_start(thread)
with patch.object(threading.Thread, 'start', controlled_start):
    app = importlib.import_module('app')
graph, pdf = app.graph, app.pdf
check(not graph.enabled(), 'Isolated copy has no Graph credentials or external sync')
server = uvicorn.Server(uvicorn.Config(app.app, host='127.0.0.1', port=PORT, log_level='error'))
worker = threading.Thread(target=server.run, daemon=True)
worker.start()
client = httpx.Client(base_url=BASE, timeout=15, trust_env=False)
for _ in range(100):
    if server.started: break
    time.sleep(.03)
check(server.started, 'Exact backend runs on isolated loopback service')
fixture = {'jobName': 'VERIFY01 release fixture', 'materials': ['Clear acrylic', 'White acrylic'],
           'materialDetails': ['DETAIL-BEGIN-01\nPolish edges; literal <b>text</b>', 'DETAIL-SECOND-02'],
           'materialCompleted': [True, False],
           'steps': [{'op': 'Cut', 'instr': 'Synthetic only'}], 'notes': '', 'image': None}
def put(state, job='VERIFY01'):
    response = client.put('/jobticket/api/' + job, json=state)
    check(response.status_code == 200 and response.json()['ok'], 'Real local PUT accepted ' + job)
def state(job='VERIFY01'):
    return client.get('/jobticket/api/' + job).json()['state']
try:
    put(fixture)
    check(state() == fixture, 'GET returns materialDetails unchanged')
    with app.db() as db:
        saved = json.loads(db.execute('SELECT data FROM tickets WHERE job_id=?', ('VERIFY01',)).fetchone()['data'])
    check(saved == fixture, 'SQLite persisted the full additive state without schema changes')
    put(fixture, 'MIXED01')
    old_client = {k: v for k, v in fixture.items() if k not in ('materialDetails', 'materialCompleted')}
    put(old_client, 'MIXED01')
    check(state('MIXED01')['materialDetails'] == fixture['materialDetails'], 'Legacy PUT preserves omitted details')
    check(state('MIXED01')['materialCompleted'] == [True, False], 'Legacy PUT preserves omitted completion')
    before = client.get('/jobticket/api/MIXED01').json()
    rejected = client.put('/jobticket/api/MIXED01', json=dict(old_client, materials=['Changed row']))
    check(rejected.status_code == 409 and client.get('/jobticket/api/MIXED01').json() == before, 'Legacy material-row change rejects without a write')
    put(dict(fixture, materialDetails=['', ''], materialCompleted=[False, False]), 'MIXED01')
    check(state('MIXED01')['materialDetails'] == ['', ''], 'Explicit updated payload clears details')
    check(state('MIXED01')['materialCompleted'] == [False, False], 'Explicit updated payload unchecks completion')
    old = {'jobName': 'LEGACY01 synthetic', 'materials': ['Existing acrylic'], 'steps': [{'op': '', 'instr': ''}]}
    put(old, 'LEGACY01')
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page_errors, external = [], []
        page.on('pageerror', lambda error: page_errors.append(str(error)))
        page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(BASE + '/') else (external.append(route.request.url), route.abort())[-1])
        page.goto(BASE + '/jobticket/VERIFY01', wait_until='networkidle')
        check(page.locator('.material-details').evaluate_all('(nodes) => nodes.map(n => n.value)') == fixture['materialDetails'], 'Actual server bootstrap restores both details')
        check(page.get_by_role('checkbox', name='Completed 1', exact=True).is_checked(), 'Actual server bootstrap restores completion')
        page.get_by_role('checkbox', name='Completed 1', exact=True).uncheck()
        page.locator('.material-details').first.fill('DETAIL-EDITED-03')
        for _ in range(100):
            if state()['materialDetails'][0] == 'DETAIL-EDITED-03': break
            page.wait_for_timeout(30)
        check(state()['materialDetails'][0] == 'DETAIL-EDITED-03', 'Browser autosave round-trips through real API and SQLite')
        page.reload(wait_until='networkidle')
        check(page.locator('.material-details').first.input_value() == 'DETAIL-EDITED-03', 'Reload restores the actual persisted edit')
        check(state()['materialCompleted'] == [False, False] and not page.get_by_role('checkbox', name='Completed 1', exact=True).is_checked(), 'Completion toggle survives actual API save/reload')
        page.locator('#matBody .row-delete').first.click()
        for _ in range(100):
            if len(state()['materials']) == 1: break
            page.wait_for_timeout(30)
        check(state()['materials'] == ['White acrylic'] and state()['materialDetails'] == ['DETAIL-SECOND-02'], 'Deletion persists aligned arrays through real backend')
        check(state()['materialCompleted'] == [False], 'Deletion persists aligned completion')
        page.goto(BASE + '/jobticket/LEGACY01', wait_until='networkidle')
        check(page.locator('#matBody input[data-row-input="mat"]').input_value() == 'Existing acrylic' and page.locator('.material-details').input_value() == '', 'Old persisted ticket restores without migration')
        check(not page.get_by_role('checkbox', name='Completed 1', exact=True).is_checked(), 'Old persisted ticket defaults completion to unchecked')
        before = state('LEGACY01')
        page.evaluate('window.confirm = () => false')
        page.evaluate('resetTicket()')
        page.wait_for_timeout(1000)
        check(state('LEGACY01') == before, 'Cancelled Reset leaves actual stored ticket unchanged')
        page.evaluate('window.confirm = () => true')
        page.evaluate('resetTicket()')
        for _ in range(100):
            if state('LEGACY01').get('materialDetails') == ['']: break
            page.wait_for_timeout(30)
        check(state('LEGACY01')['materials'] == [''] and state('LEGACY01')['materialDetails'] == [''], 'Confirmed Reset persists both blank arrays')
        check(state('LEGACY01')['materialCompleted'] == [False], 'Confirmed Reset persists unchecked completion')
        check(not page_errors and not external, 'Actual-backend browser had no errors or non-local requests')
        browser.close()

    put(fixture)
    blob = pdf.render(BASE + '/jobticket/VERIFY01')
    (ROOT / 'backend-material-details.pdf').write_bytes(blob)
    pdf_text = '\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(blob)).pages)
    check(all(s in pdf_text for s in ['DETAIL-BEGIN-01', 'DETAIL-SECOND-02', 'Polish edges', 'literal <b>text</b>', 'Clear acrylic']), 'Unmodified deployed PDF renderer prints persisted details as literal text')
    check('[x]' in pdf_text and '[ ]' in pdf_text, 'Real PDF visibly distinguishes checked and unchecked rows without color')
    long = dict(fixture, materials=['Acrylic'], materialCompleted=[True], materialDetails=['\n'.join(f'Detail line {n:03}: cut and polish' for n in range(1,181))])
    put(long)
    long_pdf = pdf.render(BASE + '/jobticket/VERIFY01')
    (ROOT / 'backend-long-details.pdf').write_bytes(long_pdf)
    long_reader = PdfReader(io.BytesIO(long_pdf))
    long_text = '\n'.join(p.extract_text() for p in long_reader.pages)
    check(all(f'Detail line {n:03}:' in long_text for n in range(1,181)), 'All 180 detail lines survive multi-page PDF rendering')

    # Exercise the exact Graph/PDF push path, intercepting only external HTTP.
    config = {k: 'LOCAL-TEST' for k in ['GRAPH_TENANT_ID','GRAPH_CLIENT_ID','GRAPH_CLIENT_SECRET','GRAPH_SITE_HOSTNAME','GRAPH_SITE_PATH']}
    graph.cfg = lambda: config
    uploaded = []
    block_upload = False
    upload_entered, release_upload = threading.Event(), threading.Event()
    def fake_graph_http(url, method='GET', data=None, headers=None, timeout=60):
        if url.startswith('https://login.microsoftonline.com/'):
            return json.dumps({'access_token': 'LOCAL-ONLY', 'expires_in': 3600}).encode()
        if method == 'GET' and '/sites/' in url and url.endswith('/drives'):
            return json.dumps({'value': []}).encode()
        if method == 'GET' and '/sites/' in url and url.endswith('/drive'):
            return json.dumps({'id': 'LOCAL-DRIVE'}).encode()
        if method == 'GET' and '/sites/' in url:
            return json.dumps({'id': 'LOCAL-SITE'}).encode()
        if method == 'PUT' and '/drives/LOCAL-DRIVE/root:/' in url and url.endswith(':/content'):
            uploaded.append({'url': url, 'blob': data})
            if block_upload:
                upload_entered.set()
                if not release_upload.wait(10): raise RuntimeError('Test upload barrier timed out')
            return json.dumps({'name': 'local.pdf', 'webUrl': 'https://invalid.example/local-only', 'size': len(data)}).encode()
        raise RuntimeError('Unexpected external transport call blocked: ' + method + ' ' + url)
    graph._req = fake_graph_http
    put(fixture)
    result = app.push_ticket('VERIFY01')
    pushed_text = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(uploaded[-1]['blob'])).pages)
    check(result['ok'] and 'DETAIL-BEGIN-01' in pushed_text, 'Exact push path passes a real details-bearing PDF to intercepted Graph transport')
    check('/VERIFY01%20release%20fixture/' in uploaded[-1]['url'], 'Graph destination derives from job name, with encoded path')
    block_upload = True
    push_result = []
    push_thread = threading.Thread(target=lambda: push_result.append(app.push_ticket('VERIFY01')))
    push_thread.start()
    check(upload_entered.wait(10), 'Concurrent-save reproduction holds the completed old PDF at upload')
    newer = dict(fixture, materialDetails=['NEWER-EDIT-NOT-IN-OLD-PDF', 'DETAIL-SECOND-02'])
    put(newer)
    release_upload.set()
    push_thread.join(10)
    sync = client.get('/jobticket/api/VERIFY01/sync').json()
    old_pdf_text = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(uploaded[-1]['blob'])).pages)
    check(push_result[0]['ok'] and state()['materialDetails'][0] == 'NEWER-EDIT-NOT-IN-OLD-PDF' and 'NEWER-EDIT-NOT-IN-OLD-PDF' not in old_pdf_text and sync['stale'] is True, 'Old PDF completion leaves the newer saved edit queued')
    block_upload = False
    check(app.push_ticket('VERIFY01')['ok'], 'Next push succeeds for the current revision')
    current_text = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(uploaded[-1]['blob'])).pages)
    check('NEWER-EDIT-NOT-IN-OLD-PDF' in current_text and client.get('/jobticket/api/VERIFY01/sync').json()['stale'] is False, 'Only the details-bearing current PDF clears queued status')
    report = {'passed': len(checks), 'checks': checks, 'long_pdf_pages': len(long_reader.pages), 'graph_transport': 'intercepted; no real Graph requests', 'database': 'isolated synthetic SQLite', 'backend_sha256': {n: hashlib.sha256((REPO / 'backend' / n).read_bytes()).hexdigest() for n in ['app.py','graph.py','pdf.py']}}
    (ROOT / 'backend-results.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
finally:
    server.should_exit = True
    worker.join(10)
    client.close()
    shutil.rmtree(isolation)
