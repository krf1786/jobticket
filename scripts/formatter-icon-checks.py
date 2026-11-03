"""Focused formatter icon checks against a disposable local ticket backend.

Run with the existing release-checks Python/Playwright environment. All fixture
data and server files live in a temporary directory; evidence is ignored output.
"""
from pathlib import Path
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.parse import unquote

import httpx
from playwright.sync_api import sync_playwright


REPO = Path(__file__).resolve().parents[1]
OUT = REPO / 'output' / 'formatter-icons'
OUT.mkdir(parents=True, exist_ok=True)
checks = []
errors = []
external = []
metrics = {}
BASELINE_HEIGHTS = {1200: 79, 390: 143, 320: 143}
LABELS = ('Bold', 'Italic', 'Underline', 'Yellow highlight', 'Pink highlight', 'Green highlight', 'Clear Formatting')
HIGHLIGHTS = (('Yellow highlight', '#fef08a'), ('Pink highlight', '#fbcfe8'), ('Green highlight', '#bbf7d0'))


def check(ok, label):
    assert ok, label
    checks.append(label)


def eventually(predicate, page):
    for _ in range(200):
        if predicate():
            return
        page.wait_for_timeout(40)
    raise AssertionError('Expected saved state did not arrive')


def select_notes(page, start=0, end=8):
    page.locator('.rich-editor[data-rich-key="notes"]').evaluate('''(el,p)=>{
        el.focus();let w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT),nodes=[],n;
        while(n=w.nextNode())nodes.push(n);
        function point(p){for(let n of nodes){if(p<=n.length)return[n,p];p-=n.length}return[nodes.at(-1),nodes.at(-1).length]}
        let r=document.createRange();r.setStart(...point(p[0]));r.setEnd(...point(p[1]));
        getSelection().removeAllRanges();getSelection().addRange(r);document.dispatchEvent(new Event('selectionchange'));
    }''', [start, end])


def notes_runs(page):
    return page.evaluate('TicketRichText.collect().richText.fields.notes || []')


def selected_notes(page):
    return page.evaluate('''()=>{let e=document.querySelector('.rich-editor[data-rich-key="notes"]'),s=getSelection();
        return s.toString()==='Selected'&&e.contains(s.anchorNode)&&e.contains(s.focusNode)}''')


with tempfile.TemporaryDirectory(prefix='ticket-icons-') as tmp:
    root = Path(tmp)
    for source in (REPO / 'backend').glob('*.py'):
        shutil.copy2(source, root / source.name)
    shutil.copy2(REPO / 'frontend/ticket.html', root / 'ticket.html')
    shutil.copytree(REPO / 'frontend/static', root / 'static')
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    base = f'http://127.0.0.1:{port}'
    api = '/jobticket/api/ICON01'
    env = {k: v for k, v in os.environ.items() if not k.startswith(('GRAPH_', 'PUSH_'))}
    log = (OUT / 'server.log').open('w')
    server = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', str(port), '--log-level', 'error'],
        cwd=root, env=env, stdout=log, stderr=log,
    )
    client = httpx.Client(base_url=base, trust_env=False, timeout=10)
    result = {}
    try:
        for _ in range(100):
            try:
                if client.get('/jobticket/health').status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(.05)
        check(client.get('/jobticket/health').json()['graph'] is False, 'Disposable backend has Graph disabled')
        fixture = dict(
            jobName='Formatter icon acceptance', date='2026-11-02', qty='7', due='2026-11-09', time='09:45',
            notes='Selected words remain selected', materials=['Acrylic'], materialDetails=['Approved details'],
            materialCompleted=[False], materialRowIds=['icon-material'], materialFiles=[None],
            materialFileBase={}, steps=[dict(op='Laser cut', instr='Approved instructions')], image=None,
        )
        client.put(api, json=fixture).raise_for_status()
        initial_state = client.get(api).json()['state']
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={'width': 1200, 'height': 1000})

            def route(r):
                if not r.request.url.startswith(base + '/'):
                    external.append(r.request.url)
                    return r.abort()
                return r.continue_()

            context.route('**/*', route)
            page = context.new_page()
            writes = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('request', lambda r: writes.append(r.url) if r.method == 'PUT' else None)
            page.goto(base + '/jobticket/ICON01', wait_until='networkidle')
            bar = page.get_by_role('toolbar', name='Text formatting', exact=True)
            check(bar.is_visible(), 'Accessible Text formatting toolbar mounts')
            page.wait_for_timeout(800)
            check(not writes and client.get(api).json()['state'] == initial_state, 'Mounting the icon toolbar issues no save or state mutation')
            check(bar.locator('button.rich-icon-button').count() == 7, 'All seven formatting actions use compact icon buttons')
            for label in LABELS:
                button = bar.get_by_role('button', name=label, exact=True)
                check(button.count() == 1 and button.get_attribute('title') == label, label + ' keeps its exact accessible name and native tooltip')
                check(button.locator(':scope > [aria-hidden="true"]').count() > 0 and label not in button.inner_text(), label + ' shows a decorative icon instead of its option text')
            check(all(bar.get_by_role('button', name=label, exact=True).locator('svg[aria-hidden="true"]').count() == 1 for label in ('Yellow highlight', 'Pink highlight', 'Green highlight', 'Clear Formatting')), 'Highlight and clear-format actions have decorative SVG icons')
            for label, _ in HIGHLIGHTS:
                colors = bar.get_by_role('button', name=label, exact=True).evaluate('''el=>[el,...el.querySelectorAll('*')].flatMap(n=>{
                    let s=getComputedStyle(n);return[s.fill,s.stroke,s.backgroundColor,s.color,s.borderBottomColor]
                })''')
                rgb_colors = [tuple(map(int, m.groups())) for value in colors if (m := re.fullmatch(r'rgb\((\d+), (\d+), (\d+)\)', value))]
                tone = {
                    'Yellow highlight': lambda r,g,b: r > 180 and g > 100 and b < 100,
                    'Pink highlight': lambda r,g,b: r > 180 and b > 80 and g < r - 30,
                    'Green highlight': lambda r,g,b: g > 100 and g > r + 30 and g > b + 30,
                }[label]
                check(any(tone(*rgb) for rgb in rgb_colors), label + ' visibly carries its distinct highlight color')
            size = bar.get_by_label('Font size', exact=True)
            color = bar.get_by_label('Text color', exact=True)
            check(size.get_attribute('title') == 'Font size' and all(o.isdigit() or o in ('', '↕') for o in size.locator('option').all_text_contents()), 'Font size retains a titled numeric native select without a text label')
            check(color.get_attribute('type') == 'color' and color.get_attribute('title') == 'Text color', 'Text color remains a titled native color input')
            color_control = bar.locator('.rich-color-control')
            check(color_control.count() == 1 and 'A' in color_control.inner_text(), 'Text color displays the familiar A indicator')
            pointer = color.evaluate('''el=>{let r=el.getBoundingClientRect();let hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                return {width:r.width,height:r.height,nativeHit:hit===el}}''')
            check(pointer['nativeHit'] and min(pointer['width'], pointer['height']) >= 24, 'Text color presents a usable native pointer target')
            bar.get_by_role('button', name='Bold', exact=True).focus()
            reached_color = False
            for _ in range(12):
                page.keyboard.press('Tab')
                if color.evaluate('el=>document.activeElement===el'):
                    reached_color = True
                    break
            check(reached_color, 'Native text color input is reachable by keyboard')
            focus_ring = color.evaluate('''el=>[el,el.closest('.rich-color-control')].some(n=>{
                let s=getComputedStyle(n);return (s.outlineStyle!=='none'&&parseFloat(s.outlineWidth)>0)||s.boxShadow!=='none'
            })''')
            check(focus_ring, 'Keyboard focus on text color has a visible control outline')
            page.locator('#jobNo').focus()
            for width in (1200, 390, 320):
                page.set_viewport_size({'width': width, 'height': 1000})
                metrics[str(width)] = page.locator('.toolbar').evaluate('''e=>{
                    let print=e.querySelector('button'),save=e.querySelector('#saveStatus'),bar=e.querySelector('.rich-toolbar');
                    let p=print.getBoundingClientRect(),s=save.getBoundingClientRect(),b=bar.getBoundingClientRect(),r=e.getBoundingClientRect();
                    return {height:r.height,width:r.width,scrollWidth:document.documentElement.scrollWidth,
                        print:{top:p.top,bottom:p.bottom,left:p.left,right:p.right},save:{top:s.top,bottom:s.bottom,left:s.left,right:s.right},
                        bar:{top:b.top,bottom:b.bottom,left:b.left,right:b.right},
                        controls:[...bar.children].map(c=>{let r=c.getBoundingClientRect();return{left:r.left,right:r.right,top:r.top,bottom:r.bottom}})}
                }''')
                m = metrics[str(width)]
                check(m['scrollWidth'] <= width + 1 and all(c['left'] >= -.5 and c['right'] <= width + .5 for c in m['controls']), 'All formatter controls fit the ' + str(width) + 'px viewport')
                check(m['height'] <= BASELINE_HEIGHTS[width] + 1, 'Toolbar height does not exceed the previous layout at ' + str(width) + 'px')
                check(abs((m['print']['top'] + m['print']['bottom']) / 2 - (m['save']['top'] + m['save']['bottom']) / 2) <= 1, 'Print and save status share a row at ' + str(width) + 'px')
                if width == 1200:
                    check(m['bar']['top'] < m['print']['bottom'] and m['bar']['bottom'] > m['print']['top'], 'Desktop Print, formatter icons, and Saved status fit on one row')
                else:
                    check(m['bar']['top'] >= m['print']['bottom'] - 1, 'Mobile formatter icons follow the Print and Saved row at ' + str(width) + 'px')
                page.screenshot(path=str(OUT / f'toolbar-{width}.png'), full_page=True)
            (OUT / 'layout-metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
            page.set_viewport_size({'width': 1200, 'height': 1000})
            for label, mark in (('Bold', 'bold'), ('Italic', 'italic'), ('Underline', 'underline')):
                select_notes(page)
                bar.get_by_role('button', name=label, exact=True).click()
                check(selected_notes(page) and notes_runs(page)[0].get(mark) is True, label + ' icon applies the mark and retains the selected text')
                check(bar.get_by_role('button', name=label, exact=True).get_attribute('aria-pressed') == 'true', label + ' exposes its selected state')
            for label, color_hex in HIGHLIGHTS:
                select_notes(page)
                bar.get_by_role('button', name=label, exact=True).click()
                check(selected_notes(page) and notes_runs(page)[0].get('highlight') == color_hex, label + ' icon preserves the selection and exact highlight')
            select_notes(page)
            size.select_option('24')
            check(selected_notes(page) and notes_runs(page)[0].get('size') == 24 and size.input_value() == '24', 'Numeric size control applies 24px and retains the selection')
            color.fill('#123456')
            color.dispatch_event('input')
            check(selected_notes(page) and notes_runs(page)[0].get('color') == '#123456' and color.input_value() == '#123456', 'Native text color applies the selected color and retains the selection')
            indicator_colors = color_control.evaluate('''el=>[el,...el.querySelectorAll('*')].flatMap(n=>{
                let a=[getComputedStyle(n),getComputedStyle(n,'::before'),getComputedStyle(n,'::after')];
                return a.flatMap(s=>[s.color,s.fill,s.stroke,s.backgroundColor,s.borderBottomColor,s.textDecorationColor])
            })''')
            check('rgb(18, 52, 86)' in indicator_colors, 'A indicator underline reflects the current text color')
            select_notes(page, 0, 18)
            check(size.input_value() == '', 'Mixed-size selection shows the compact placeholder')
            select_notes(page)
            check(size.input_value() == '24' and color.input_value() == '#123456', 'Selecting formatted text updates size and native color values')
            bar.get_by_role('button', name='Clear Formatting', exact=True).click()
            check(selected_notes(page) and not notes_runs(page), 'Clear-format icon restores defaults and retains selection')
            headers = page.locator('table.materials-data thead th').all_text_contents()
            check(headers[:2] == ['QTY', 'Material'], 'QTY remains left of Material')
            quantity = page.locator('.material-quantity').first
            page.get_by_role('button', name='Increase material quantity 1', exact=True).click()
            check(quantity.input_value() == '1', 'Existing QTY increase arrow still increments')
            page.get_by_role('button', name='Decrease material quantity 1', exact=True).click()
            check(quantity.input_value() == '0', 'Existing QTY decrease arrow still decrements')
            eventually(lambda: client.get(api).json()['state'].get('materialQuantities') == ['0'], page)
            saved_state = client.get(api).json()['state']
            writes.clear()
            page.reload(wait_until='networkidle')
            page.wait_for_timeout(800)
            check(not writes and client.get(api).json()['state'] == saved_state, 'Reloading the saved icon toolbar makes no render-triggered save')
            page.emulate_media(media='print')
            check(not bar.is_visible() and not page.locator('.rich-icon-button').first.is_visible() and not color_control.is_visible(), 'Print output hides every formatter icon and color control')
            page.screenshot(path=str(OUT / 'print.png'), full_page=True)
            page.emulate_media(media='screen')
            parent = context.new_page()
            parent.goto(base + '/jobticket/', wait_until='networkidle')
            exported = parent.evaluate('''url=>new Promise((resolve,reject)=>{
                let f=document.createElement('iframe');f.src=url;document.body.append(f);
                let timer=setTimeout(()=>reject(Error('preview export timeout')),15000);
                addEventListener('message',e=>{if(e.source===f.contentWindow&&e.data.type==='jplak:preview-response'){
                    clearTimeout(timer);resolve(e.data)}});
                f.onload=()=>f.contentWindow.postMessage({type:'jplak:preview-request',requestId:'formatter-icons'},location.origin)
            })''', base + '/jobticket/ICON01')
            check(not exported.get('error') and exported.get('image', '').startswith('data:image/svg+xml'), 'Actual corkboard export still produces a ticket SVG')
            svg = unquote(exported['image'].split(',', 1)[1])
            (OUT / 'corkboard-preview.svg').write_text(svg)
            snapshot = context.new_page()
            snapshot.set_content(svg)
            check(not snapshot.locator('.rich-toolbar').is_visible() and not snapshot.locator('.rich-icon-button').first.is_visible(), 'Corkboard SVG output hides the new formatter icons')
            parent.close()
            snapshot.close()
            check(not errors and not external, 'No browser errors or requests outside the disposable local server')
            browser.close()
        result = {'passed': len(checks), 'checks': checks, 'metrics': metrics, 'scope': 'Disposable backend and synthetic ticket only'}
    except Exception:
        result = {'passed_before_failure': len(checks), 'checks': checks, 'error': traceback.format_exc(), 'page_errors': errors, 'external': external, 'metrics': metrics}
        raise
    finally:
        (OUT / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        client.close()
        server.terminate()
        server.wait(timeout=8)
        log.close()
