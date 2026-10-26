"""Real isolated API/SQLite/browser attachment workflow; never contacts production."""
from pathlib import Path
import hashlib,json,os,shutil,socket,subprocess,sys,tempfile,time,traceback,uuid
import httpx
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
REPO=Path(__file__).resolve().parents[1]
OUT=REPO/'output'/'attachments';OUT.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];external=[]
def check(value,label):
    assert value,label
    checks.append(label)
def eventually(predicate,label,page):
    for _ in range(180):
        if predicate():return
        page.wait_for_timeout(30)
    raise AssertionError(label)
with tempfile.TemporaryDirectory(prefix='jobticket-attachment-ui-') as directory:
    root=Path(directory)
    for source in (REPO/'backend').glob('*.py'):shutil.copy2(source,root/source.name)
    shutil.copy2(REPO/'frontend/ticket.html',root/'ticket.html')
    shutil.copytree(REPO/'frontend/static',root/'static')
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    base='http://127.0.0.1:'+str(port)
    env={k:v for k,v in os.environ.items() if not k.startswith(('GRAPH_','PUSH_'))};env['PORT']=str(port);env['PYTHONDONTWRITEBYTECODE']='1'
    # Inject latency/failure at the isolated HTTP boundary; core handlers/storage stay real.
    (root/'attachment_test_server.py').write_text("""
import asyncio,time
from pathlib import Path
from fastapi.responses import JSONResponse
import app
root=Path(__file__).parent
async def application(scope,receive,send):
    path=scope.get('path','');method=scope.get('method','')
    if method=='POST' and path=='/jobticket/api/FILES01/attachments' and (root/'fail-upload').exists():
        return await JSONResponse({'detail':'Synthetic upload failure'},status_code=503)(scope,receive,send)
    gate='upload' if method=='POST' and path=='/jobticket/api/FILES01/attachments' else 'save' if method=='PUT' and path=='/jobticket/api/FILES01' else None
    if gate and (root/('hold-'+gate)).exists():
        messages=[]
        async def capture(message):messages.append(message)
        await app.app(scope,receive,capture)
        (root/(gate+'-held')).touch()
        start=time.monotonic()
        while (root/('hold-'+gate)).exists() and time.monotonic()-start<15:await asyncio.sleep(.02)
        for message in messages:await send(message)
    else:await app.app(scope,receive,send)
""")
    log=(OUT/'server.log').open('w')
    server=subprocess.Popen([sys.executable,'-m','uvicorn','attachment_test_server:application','--host','127.0.0.1','--port',str(port),'--log-level','error'],cwd=root,env=env,stdout=log,stderr=log)
    client=httpx.Client(base_url=base,timeout=10,trust_env=False)
    try:
        for _ in range(100):
            try:
                if client.get('/jobticket/health').status_code==200:break
            except httpx.TransportError:pass
            time.sleep(.05)
        check(client.get('/jobticket/health').json()['graph'] is False,'Isolated service has Graph disabled')
        def state():return client.get('/jobticket/api/FILES01').json()['state']
        fixture={'jobName':'FILES01 synthetic attachments','materials':['Acrylic','Acrylic'],'materialDetails':['Front layer','Back layer'],'materialCompleted':[False,False],'steps':[{'op':'Cut','instr':''}],'date':'2026-10-26','time':'10:00','notes':'','image':None}
        def reset_fixture():
            previous=client.get('/jobticket/api/FILES01')
            old=previous.json()['state'] if previous.status_code==200 else {}
            payload=dict(fixture,materialRowIds=['__proto__',uuid.uuid4().hex],materialFiles=[None,None],materialFileBase={rid:(file or {}).get('id') for rid,file in zip(old.get('materialRowIds',[]),old.get('materialFiles',[]))})
            check(client.put('/jobticket/api/FILES01',json=payload).status_code==200,'Synthetic fixture can be reset intentionally')
        reset_fixture();board_before=client.get('/jobticket/corkboard/api').json()
        with sync_playwright() as pw:
            browser=pw.chromium.launch();context=browser.new_context(viewport={'width':1200,'height':1100});page=context.new_page()
            context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base+'/') else (external.append(route.request.url),route.abort())[-1])
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/jobticket/',wait_until='networkidle')
            check(page.get_by_role('button',name='Attach file to material 1',exact=True).count()==1,'Material rows offer an attachment control')
            check(page.get_by_role('button',name='Attach file to material 1',exact=True).is_disabled(),'Scratch tickets cannot create persistent server attachments')
            page.goto(base+'/jobticket/FILES01',wait_until='networkidle')
            original=b'%PDF-1.4\nSYNTHETIC FRONT LAYER\n%%EOF'
            name='Front <draft> layer.pdf'
            page.locator('.material-file-input').nth(0).set_input_files({'name':name,'mimeType':'application/pdf','buffer':original})
            eventually(lambda:bool(state().get('materialFiles',[None])[0]),'Attachment did not save',page)
            saved=state();first=saved['materialFiles'][0]
            check(first['name']==name and len(set(saved['materialRowIds']))==2,'Upload saves metadata with unique row identities')
            check(client.get(first['url']).content==original,'Download returns exact original bytes')
            with page.expect_download() as downloaded:page.locator('.material-file-download').first.click()
            download=downloaded.value;download.save_as(OUT/'downloaded.pdf')
            check((OUT/'downloaded.pdf').read_bytes()==original and download.suggested_filename.endswith('layer.pdf'),'Browser Download delivers original bytes with the file name')
            page.locator('#notes').fill('Attachment baseline supports valid row identifiers')
            eventually(lambda:state()['notes']=='Attachment baseline supports valid row identifiers','Attachment row identifier prevents later save',page)
            check(True,'A valid special row identifier retains attachments through later saves')
            page.reload(wait_until='networkidle')
            check(page.locator('.material-file-download').first.text_content()==name and page.locator('.material-file-download b').count()==0,'Reload restores literal filename without interpreting markup')
            second_data=b'SYNTHETIC BACK LAYER AI BYTES'
            page.locator('.material-file-input').nth(1).set_input_files({'name':'Back-layer.ai','mimeType':'application/postscript','buffer':second_data})
            eventually(lambda:bool(state()['materialFiles'][1]),'Second row did not save',page);second=state()['materialFiles'][1]
            page.locator('#matBody .row-delete').first.click()
            eventually(lambda:len(state()['materials'])==1,'Deletion did not save',page)
            check(state()['materialDetails']==['Back layer'] and state()['materialFiles'][0]['id']==second['id'],'Deleting a duplicate-name row preserves the other row attachment')
            check(page.get_by_role('button',name='Replace file for material 1',exact=True).count()==1,'Attachment labels follow remaining row order')
            page.locator('.material-file-input').first.set_input_files({'name':'Bad replacement.ai','mimeType':'application/postscript','buffer':b'REPLACEMENT'})
            eventually(lambda:state()['materialFiles'][0]['name']=='Bad replacement.ai','Replacement did not save',page)
            retained=state()['materialFiles'][0]
            (root/'fail-upload').touch()
            page.locator('.material-file-input').first.set_input_files({'name':'Failed.ai','mimeType':'application/postscript','buffer':b'FAIL'})
            eventually(lambda:page.locator('.material-file-status').first.is_visible() and 'failed' in page.locator('.material-file-status').first.text_content().lower(),'Upload failure not shown',page)
            check(state()['materialFiles'][0]['id']==retained['id'] and page.locator('.material-file-download').first.text_content()==retained['name'],'Failed replacement retains previous attachment and download')
            (root/'fail-upload').unlink()
            with page.expect_file_chooser() as chooser:page.get_by_role('button',name='Replace file for material 1',exact=True).press('Enter')
            check(page.locator('#matBody tr').count()==1,'Enter activates Replace without adding a material row')
            chooser.value.set_files({'name':'Keyboard-layer.ai','mimeType':'application/postscript','buffer':b'KEYBOARD'})
            eventually(lambda:state()['materialFiles'][0]['name']=='Keyboard-layer.ai','Keyboard replacement did not save',page)
            page.locator('.material-details').first.press('Enter')
            check(page.locator('#matBody tr').count()==2,'Enter in details still adds the next material row')
            eventually(lambda:len(state()['materials'])==2,'Added row did not save',page)
            (root/'hold-upload').touch()
            page.locator('.material-file-input').nth(1).set_input_files({'name':'Deleted-row.ai','mimeType':'application/postscript','buffer':b'DELETED ROW'})
            eventually(lambda:(root/'upload-held').exists(),'Upload response not held',page)
            check(page.evaluate("()=>!window.dispatchEvent(new Event('beforeunload',{cancelable:true}))"),'Pending upload protects against leaving the page')
            page.locator('#matBody .row-delete').nth(1).click()
            (root/'hold-upload').unlink()
            eventually(lambda:len(state()['materials'])==1,'Deleted pending row persisted',page)
            check(state()['materialFiles'][0]['name']=='Keyboard-layer.ai','Deleting during upload cannot attach returned file to another row')
            page.evaluate('''()=>{const file=new File([new ArrayBuffer(104857601)],'Too-large.ai');const dt=new DataTransfer();dt.items.add(file);const input=document.querySelector('.material-file-input');input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}));}''')
            eventually(lambda:'100' in page.locator('.material-file-status').first.text_content(),'Oversize selection not rejected',page)
            check(state()['materialFiles'][0]['name']=='Keyboard-layer.ai','Oversize selection preserves previous attachment')
            page.reload(wait_until='networkidle')
            for width in [1200,390,320]:
                page.set_viewport_size({'width':width,'height':1100})
                check(page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth+1'),f'Attachment row stays within {width}px viewport')
                check(page.locator('.material-file-download').first.evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'),f'Typical attachment filename remains readable at {width}px')
            page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
            page.set_viewport_size({'width':1200,'height':1100});page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
            page.emulate_media(media='print');page.pdf(path=str(OUT/'attachments-letter.pdf'),format='Letter',print_background=True)
            printed=PdfReader(OUT/'attachments-letter.pdf')
            text='\n'.join(p.extract_text() for p in printed.pages)
            uris=[str(annotation.get_object().get('/A',{}).get('/URI','')) for sheet in printed.pages for annotation in sheet.get('/Annots',[])]
            check(not any(uri.startswith(base) for uri in uris),'Printed filenames do not embed broken loopback download links')
            check('Keyboard-layer.ai' in text and not page.locator('.material-file-replace').first.is_visible(),'Print includes filename while hiding editing controls')
            page.emulate_media(media='screen')
            other=context.new_page();other.goto(base+'/jobticket/FILES01',wait_until='networkidle')
            (root/'hold-save').touch()
            page.locator('#notes').fill('Save held while file uploads')
            eventually(lambda:(root/'save-held').exists(),'Form save not held',page)
            page.locator('.material-file-input').first.set_input_files({'name':'Current-layer.ai','mimeType':'application/postscript','buffer':b'CURRENT LAYER'})
            eventually(lambda:page.locator('.material-file-download').first.text_content()=='Current-layer.ai','Concurrent upload not displayed',page)
            (root/'hold-save').unlink()
            eventually(lambda:state()['materialFiles'][0]['name']=='Current-layer.ai','File upload lost during held form save',page)
            check(state()['notes']=='Save held while file uploads','File uploaded during a pending save persists with the later edit')
            other.locator('#notes').fill('Stale tab must not erase newer attachment')
            eventually(lambda:'changed elsewhere' in other.locator('#saveStatus').text_content(),'Stale save conflict not displayed',other)
            check(state()['materialFiles'][0]['name']=='Current-layer.ai' and state()['notes']=='Save held while file uploads','Stale browser tab cannot erase a newer attachment or acknowledge its save')
            other.close()
            page.get_by_role('button',name='Remove file from material 1',exact=True).press('Enter')
            eventually(lambda:state()['materialFiles'][0] is None,'Removal not saved',page)
            check(page.locator('#matBody tr').count()==1 and client.get(first['url']).content==original,'Removing reference retains row and older uploaded bytes')
            heights=page.evaluate("()=>[document.querySelector('#matBody tr').getBoundingClientRect().height,document.querySelector('#prodBody tr').getBoundingClientRect().height]")
            check(abs(heights[0]-heights[1])<=1,'Empty attachment row retains compact Production Step height')
            check(client.get('/jobticket/corkboard/api').json()==board_before,'Attachment edits leave corkboard data unchanged')
            check(not errors and not external,'No browser errors or external requests')
            context.close();browser.close()
        report={'passed':len(checks),'checks':checks,'page_errors':errors,'external_requests':external,'scope':'Real isolated backend and synthetic files; no production calls'}
        (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    except Exception:
        print(json.dumps({'passed_before_failure':len(checks),'checks':checks,'error':traceback.format_exc()}));raise
    finally:
        client.close();server.terminate()
        try:server.wait(timeout=8)
        except subprocess.TimeoutExpired:server.kill();server.wait()
        log.close()
