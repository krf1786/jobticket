"""Disposable real API/browser formatting and material-QTY acceptance checks."""
from pathlib import Path
import copy, json, os, shutil, socket, subprocess, sys, tempfile, time, traceback
import httpx
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

REPO=Path(__file__).resolve().parents[1]
OUT=REPO/'output'/'formatting'; OUT.mkdir(parents=True,exist_ok=True)
checks=[]; errors=[]; external=[]
def check(ok,label):
    assert ok,label
    checks.append(label)
def eventually(predicate,page):
    for _ in range(250):
        if predicate(): return
        page.wait_for_timeout(40)
    raise AssertionError('Autosave did not reach expected state')

with tempfile.TemporaryDirectory(prefix='ticket-formatting-') as tmp:
    root=Path(tmp)
    for source in (REPO/'backend').glob('*.py'): shutil.copy2(source,root/source.name)
    shutil.copy2(REPO/'frontend/ticket.html',root/'ticket.html')
    shutil.copytree(REPO/'frontend/static',root/'static')
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    base=f'http://127.0.0.1:{port}';api='/jobticket/api/FMT01'
    env={k:v for k,v in os.environ.items() if not k.startswith(('GRAPH_','PUSH_'))}
    log=(OUT/'server.log').open('w')
    server=subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port',str(port),'--log-level','error'],cwd=root,env=env,stdout=log,stderr=log)
    client=httpx.Client(base_url=base,trust_env=False,timeout=10)
    def ticket():
        r=client.get(api);r.raise_for_status();return r.json()
    def state():return ticket()['state']
    try:
        for _ in range(100):
            try:
                if client.get('/jobticket/health').status_code==200:break
            except httpx.TransportError:pass
            time.sleep(.05)
        check(client.get('/jobticket/health').json()['graph'] is False,'Isolated backend has Graph disabled')
        fixture=dict(jobName='FMT01 café 🐂 original',date='2026-11-02',qty='7',due='2026-11-09',time='09:45',notes='Notes café 🐂\nSecond line',materials=['Acrylic','Acrylic'],materialDetails=['First details','Second details'],materialCompleted=[False,True],materialRowIds=['row-first','row-second'],materialFiles=[None,None],materialFileBase={},steps=[dict(op='Laser cut',instr='Approved instructions\nSecond line')],image=None)
        check(client.put(api,json=fixture).status_code==200,'Synthetic duplicate-row fixture created')
        original=b'%PDF-1.4\nORIGINAL PRODUCTION BYTES\n%%EOF'
        upload=client.post(api+'/attachments',files={'file':('approved.ai',original,'application/postscript')});upload.raise_for_status();attachment=upload.json()['file']
        fixture=state();fixture.update(materialFiles=[attachment,None],materialFileBase={'row-first':None,'row-second':None})
        check(client.put(api,json=fixture).status_code==200,'Original-byte attachment fixture saved')
        board=client.get('/jobticket/corkboard/api').json()
        with sync_playwright() as pw:
            browser=pw.chromium.launch();context=browser.new_context(viewport={'width':1200,'height':1100})
            def route(r):
                if not r.request.url.startswith(base+'/'):external.append(r.request.url);return r.abort()
                return r.continue_()
            context.route('**/*',route)
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/jobticket/FMT01',wait_until='networkidle')
            check(page.locator('.material-quantity').count()==2,'Each material has native QTY input')
            check(page.locator('.rich-editor').count()==8,'All six prose categories mount visible editors')
            def editor(key):return page.locator('.rich-editor[data-rich-key="'+key+'"]')
            def select(key,start=0,end=None):
                editor(key).evaluate('''(el,p)=>{el.focus();const w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT),nodes=[];while(w.nextNode())nodes.push(w.currentNode);let a=p[0],b=p[1]===null?el.textContent.length:p[1],r=document.createRange(),offset=0;for(const n of nodes){if(a>=offset&&a<=offset+n.length){r.setStart(n,a-offset);break}offset+=n.length}offset=0;for(const n of nodes){if(b>=offset&&b<=offset+n.length){r.setEnd(n,b-offset);break}offset+=n.length}const s=getSelection();s.removeAllRanges();s.addRange(r);document.dispatchEvent(new Event('selectionchange'));}''',[start,end])
            keys=page.locator('.rich-editor').evaluate_all('(els)=>els.map(e=>e.dataset.richKey)')
            for key in keys:
                select(key,0,3);page.get_by_role('button',name='Bold',exact=True).click()
            eventually(lambda:all(any('bold' in r for r in state().get('richText',{}).get('fields',{}).get(k,[])) for k in keys),page)
            check(all(any('bold' in r for r in state()['richText']['fields'][k]) for k in keys),'Selected words in every prose field save explicit bold overrides')
            select('notes',0,5)
            for label in ('Italic','Underline'):
                page.get_by_role('button',name=label,exact=True).click()
            # Toolbar names form the shared editor module's accessibility contract.
            page.get_by_label('Font size',exact=True).select_option('24')
            page.get_by_label('Text color',exact=True).fill('#123456')
            page.get_by_label('Text color',exact=True).dispatch_event('input')
            for label,color in [('Yellow highlight','#fef08a'),('Pink highlight','#fbcfe8'),('Green highlight','#bbf7d0')]:
                select('notes',0,5);page.get_by_role('button',name=label,exact=True).click()
                check(any(r.get('highlight')==color for r in page.evaluate('TicketRichText.collect().richText.fields.notes')),'Selected '+label+' is represented exactly')
            runs=page.evaluate('TicketRichText.collect().richText.fields.notes')
            check(any(r.get('italic') and r.get('underline') and r.get('size')==24 and r.get('color')=='#123456' for r in runs),'Mixed italic underline size and text color coexist')
            select('notes',0,5);page.get_by_role('button',name='Clear Formatting',exact=True).click()
            check(not any(any(k!='text' for k in r) for r in page.evaluate('TicketRichText.collect().richText.fields.notes || []')),'Clear restores default marks')
            select('notes',0,0);page.get_by_role('button',name='Bold',exact=True).click();page.keyboard.insert_text('NEW ')
            before=editor('notes').inner_text();page.keyboard.press('ControlOrMeta+z');check(editor('notes').inner_text()!=before,'Undo restores text after collapsed formatted typing')
            page.keyboard.press('ControlOrMeta+Shift+z');check(editor('notes').inner_text()==before,'Redo restores collapsed formatted typing')
            hostile='<img src=x onerror=alert(1)> & café 🐂'
            editor('notes').evaluate('''(el,text)=>{el.focus();const d=new DataTransfer();d.setData('text/plain',text);d.setData('text/html','<img src=x onerror="alert(1)">');el.dispatchEvent(new ClipboardEvent('paste',{clipboardData:d,bubbles:true,cancelable:true}));}''',hostile)
            check(editor('notes').locator('img,script').count()==0 and hostile in editor('notes').inner_text(),'Hostile clipboard HTML becomes exact literal text')
            quantities=page.locator('.material-quantity');check(quantities.nth(0).input_value()=='','QTY defaults blank')
            quantities.nth(1).fill('12');eventually(lambda:state().get('materialQuantities')==['','12'],page)
            quantities.nth(1).fill(' 12 ')
            check(quantities.nth(1).input_value()=='12','QTY trims harmless outer whitespace')
            for invalid in ['1.5','-2','1234567890','abc']:
                quantities.nth(1).evaluate("(el,text)=>{const d=new DataTransfer();d.setData('text/plain',text);el.dispatchEvent(new ClipboardEvent('paste',{clipboardData:d,bubbles:true,cancelable:true}));}",invalid)
                check(quantities.nth(1).input_value()=='12','Invalid QTY paste preserves prior integer: '+invalid)
            quantities.nth(1).fill('1.5')
            check(quantities.nth(1).input_value()=='12' and quantities.nth(1).get_attribute('aria-invalid')=='true','Invalid fallback input restores valid quantity with field feedback')
            editor('notes').fill('Prose saves after rejected QTY')
            eventually(lambda:state()['notes']=='Prose saves after rejected QTY',page)
            check(state()['materialQuantities']==['','12'] and 'quantity' in page.locator('#saveStatus').inner_text().lower(),'Other prose autosaves without falsely acknowledging rejected QTY')
            quantities.nth(1).fill('14');eventually(lambda:state()['materialQuantities']==['','14'],page)
            check(quantities.nth(1).get_attribute('aria-invalid') is None,'Valid correction clears quantity feedback')
            quantities.nth(1).fill('12');eventually(lambda:state()['materialQuantities']==['','12'],page)
            page.locator('#matBody tr').nth(0).locator('.row-delete').click()
            eventually(lambda:state().get('materialQuantities')==['12'],page)
            check(state()['materialRowIds']==['row-second'] and state()['materialCompleted']==[True],'Duplicate deletion keeps QTY and completion with stable second row')
            # Native row shortcuts are exercised through the actual visible editor.
            details_key='material:row-second:details'
            editor(details_key).click();page.keyboard.press('End');page.keyboard.press('Shift+Enter');page.keyboard.insert_text('continued')
            check('\ncontinued' in page.locator('.material-details').input_value(),'Details Shift+Enter inserts a literal line break')
            count=page.locator('#matBody tr').count();page.keyboard.press('Enter')
            check(page.locator('#matBody tr').count()==count+1,'Details Enter adds a material row')
            page.locator('#matBody tr').last.locator('.row-delete').click()
            operation=next(k for k in keys if k.startswith('production:') and k.endswith(':instr'))
            editor(operation).click();page.keyboard.press('End');page.keyboard.press('Enter');page.keyboard.insert_text('continued')
            check('\ncontinued' in page.locator('textarea[data-rich-key="'+operation+'"]').input_value(),'Production instruction Enter inserts a line break')
            opkey=operation[:-5]+'op';editor(opkey).click();page.keyboard.press('Enter')
            check(page.locator('#prodBody tr').count()==2,'Production operation Enter adds a row')
            page.locator('#prodBody tr').last.locator('.row-delete').click()
            editor('material:row-second:name').click();page.get_by_role('button',name='Material suggestions').click()
            options=page.locator('.rich-suggestions [role=option]:visible');check(options.count()>0,'Material suggestions retain accessible options')
            options.first.click();eventually(lambda:state()['materials'][0]!='Acrylic',page)
            # A failed autosave stays visible, then a real subsequent edit recovers.
            page.route('**'+api,lambda r:r.fulfill(status=503,content_type='application/json',body='{"detail":"synthetic save failure"}') if r.request.method=='PUT' else r.continue_())
            editor('notes').fill('Failed save retry text');eventually(lambda:'not saved' in page.locator('#saveStatus').inner_text().lower(),page)
            check(state()['notes']!='Failed save retry text','Failed autosave does not claim a persisted change')
            page.unroute('**'+api);editor('notes').fill('Recovered save text');eventually(lambda:state()['notes']=='Recovered save text',page)
            # Insert a newer formatted edit while the first PUT response is withheld.
            delayed=[False]
            def slow_ack(r):
                if r.request.method!='PUT' or delayed[0]:return r.continue_()
                delayed[0]=True;response=r.fetch()
                editor('notes').fill('Newer edit during acknowledgement')
                select('notes',0,5);page.get_by_role('button',name='Bold',exact=True).click()
                return r.fulfill(response=response)
            page.route('**'+api,slow_ack)
            editor('notes').fill('Older in-flight snapshot')
            eventually(lambda:state()['notes']=='Newer edit during acknowledgement' and bool(state().get('richText',{}).get('fields',{}).get('notes')),page)
            page.unroute('**'+api)
            check(delayed[0],'Slow acknowledgement preserves a newer formatted edit')
            saved=state();page.reload(wait_until='networkidle');check(state()==saved and quantities.nth(0).input_value()=='12','Exact saved sidecar strings and QTY survive reload')
            check(page.locator('#jobNo').input_value()=='FMT01','Saved header routing identity survives formatting')
            page.get_by_role('checkbox',name='Variable Data',exact=True).check();eventually(lambda:state().get('variableData') is True,page)
            legacy={k:v for k,v in state().items() if k not in ('richText','richTextBase','materialQuantities')}
            check(client.put(api,json=legacy).status_code==200 and state()['materialQuantities']==['12'],'Unchanged old-tab save preserves formatting and QTY')
            stale=copy.deepcopy(state());stale['richTextBase']={'version':1,'fields':{}}
            check(client.put(api,json=stale).status_code==409,'Stale formatting baseline is rejected')
            check(client.get(attachment['url']).content==original,'Original uploaded attachment bytes remain intact')
            long='\n'.join(f'Print line {i:03d} café 🐂 complete details' for i in range(90))
            editor('notes').fill(long);select('notes',0,10);page.get_by_role('button',name='Bold',exact=True).click()
            eventually(lambda:state()['notes']==long,page)
            select('notes',0,10);page.get_by_role('button',name='Pink highlight',exact=True).click()
            page.get_by_label('Text color',exact=True).fill('#123456');page.get_by_label('Text color',exact=True).dispatch_event('input')
            eventually(lambda:any(r.get('highlight')=='#fbcfe8' for r in state()['richText']['fields']['notes']),page)
            page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
            for width in (390,320):
                page.set_viewport_size({'width':width,'height':1100});select('notes',0,10);page.get_by_role('button',name='Italic',exact=True).click()
                check(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Toolbar and ticket fit narrow '+str(width))
                usable=page.locator('.rich-editor[data-rich-key="material:row-second:details"]').evaluate('e=>{const s=getComputedStyle(e);return e.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)}')
                check(usable>=60,'Material details usable text width >=60px at '+str(width)+' (actual '+str(usable)+')')
                page.screenshot(path=str(OUT/f'narrow-{width}.png'),full_page=True)
            page.set_viewport_size({'width':1200,'height':1100});page.emulate_media(media='print')
            check(not page.get_by_role('button',name='Bold',exact=True).is_visible(),'Formatting toolbar hidden in print')
            pdf=OUT/'long-formatted.pdf';page.pdf(path=str(pdf),format='Letter',print_background=True)
            text='\n'.join(p.extract_text() or '' for p in PdfReader(pdf).pages)
            check('Print line 000' in text and 'Print line 089' in text and '12' in text,'Long formatted PDF retains first and last lines and QTY')
            page.emulate_media(media='screen')
            # Exercise the existing postMessage exporter from a real same-origin parent.
            parent=context.new_page();parent.goto(base+'/jobticket/',wait_until='networkidle')
            exported=parent.evaluate('''url=>new Promise((resolve,reject)=>{const f=document.createElement('iframe');f.src=url;document.body.append(f);let timer=setTimeout(()=>reject(Error('preview export timeout')),15000);addEventListener('message',e=>{if(e.source===f.contentWindow&&e.data.type==='jplak:preview-response'){clearTimeout(timer);resolve(e.data)}});f.onload=()=>f.contentWindow.postMessage({type:'jplak:preview-request',requestId:'formatting-check'},location.origin);})''',base+'/jobticket/FMT01')
            check(not exported.get('error') and exported.get('image','').startswith('data:image/svg+xml'),'Corkboard visual preview exports formatted ticket')
            svg=__import__('urllib.parse',fromlist=['unquote']).unquote(exported['image'].split(',',1)[1]);(OUT/'corkboard-preview.svg').write_text(svg)
            check('Print line 089' in svg and 'rich-editor' in svg,'Corkboard export retains full formatted editor text')
            parent.close()
            check(client.get('/jobticket/corkboard/api').json()==board,'Ticket edits do not alter corkboard records')
            touch=browser.new_context(viewport={'width':390,'height':900},has_touch=True,is_mobile=True)
            touch.route('**/*',route);tp=touch.new_page();tp.goto(base+'/jobticket/FMT01',wait_until='networkidle')
            tp.locator('.rich-editor[data-rich-key="notes"]').tap()
            tp.locator('.rich-editor[data-rich-key="notes"]').evaluate('''el=>{let n=el.firstChild.firstChild,r=document.createRange();r.setStart(n,0);r.setEnd(n,5);let s=getSelection();s.removeAllRanges();s.addRange(r);document.dispatchEvent(new Event('selectionchange'));}''')
            tp.get_by_role('button',name='Underline',exact=True).tap()
            check(any(r.get('underline') for r in tp.evaluate('TicketRichText.collect().richText.fields.notes')),'Touch tap applies toolbar formatting without losing selection')
            tp.goto(base+'/jobticket/',wait_until='networkidle');scratch_writes=[]
            tp.on('request',lambda req:scratch_writes.append(req.url) if req.method=='PUT' else None)
            tp.set_viewport_size({'width':1200,'height':1100})
            row_heights=tp.evaluate('({material:document.querySelector("#matBody tr").getBoundingClientRect().height,production:document.querySelector("#prodBody tr").getBoundingClientRect().height})')
            check(abs(row_heights['material']-row_heights['production'])<=1 and row_heights['material']<=22,'Unformatted empty material and production rows retain compact matching height '+str(row_heights))
            tp.locator('.rich-editor[data-rich-key="notes"]').fill('Scratch formatted text')
            tp.locator('.material-quantity').first.fill('12');tp.wait_for_timeout(900)
            check(not scratch_writes and client.get('/jobticket/health').json()['tickets']==1,'Scratch prose and QTY edits issue no ticket saves')
            touch.close()
            check(not errors and not external,'No browser errors or nonlocal requests')
            browser.close()
        result={'passed':len(checks),'checks':checks,'scope':'Disposable backend and synthetic ticket only'}
    except Exception:
        result={'passed_before_failure':len(checks),'checks':checks,'error':traceback.format_exc(),'page_errors':errors,'external':external}
        raise
    finally:
        (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
        client.close();server.terminate();server.wait(timeout=8);log.close()
