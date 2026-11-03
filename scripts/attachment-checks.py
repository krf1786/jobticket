"""Real isolated API/SQLite/browser multi-attachment workflow; no production calls."""
from pathlib import Path
import json,os,shutil,socket,subprocess,sys,tempfile,time,traceback,uuid
import httpx
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

REPO=Path(__file__).resolve().parents[1]
OUT=REPO/'output'/'attachments';OUT.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];external=[];writes=[]
def check(value,label):
    assert value,label
    checks.append(label)
def eventually(predicate,label,page):
    for _ in range(240):
        if predicate():return
        page.wait_for_timeout(30)
    raise AssertionError(label)
def row_files(state,index=0):
    value=state.get('materialFiles',[])[index]
    return value if isinstance(value,list) else [value] if value else []
def row_ids(state,index=0):return [file['id'] for file in row_files(state,index)]
def upload_file(name,data):return {'name':name,'mimeType':'application/octet-stream','buffer':data}

with tempfile.TemporaryDirectory(prefix='jobticket-attachment-ui-') as directory:
    root=Path(directory)
    for source in (REPO/'backend').glob('*.py'):shutil.copy2(source,root/source.name)
    shutil.copy2(REPO/'frontend/ticket.html',root/'ticket.html')
    shutil.copytree(REPO/'frontend/static',root/'static')
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    base='http://127.0.0.1:'+str(port);api='/jobticket/api/FILES01'
    env={k:v for k,v in os.environ.items() if not k.startswith(('GRAPH_','PUSH_'))}
    env.update(PORT=str(port),PYTHONDONTWRITEBYTECODE='1')
    # Faults/delays occur only at the disposable HTTP boundary; handlers/storage stay real.
    (root/'attachment_test_server.py').write_text("""
import asyncio,time
from pathlib import Path
from fastapi.responses import JSONResponse
import app
root=Path(__file__).parent
async def application(scope,receive,send):
    path=scope.get('path','');method=scope.get('method','')
    if method=='POST' and path=='/jobticket/api/FILES01/attachments':
        once=root/'fail-once-upload'
        if once.exists():
            once.unlink()
            return await JSONResponse({'detail':'Synthetic upload failure'},status_code=503)(scope,receive,send)
        if (root/'fail-upload').exists():
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
        def state():return client.get(api).json()['state']
        fixture={'jobName':'FILES01 synthetic attachments','materials':['Acrylic','Acrylic'],'materialDetails':['Front layer','Back layer'],'materialCompleted':[False,False],'steps':[{'op':'Cut','instr':''}],'date':'2026-10-26','time':'10:00','notes':'','image':None,'materialRowIds':['__proto__',uuid.uuid4().hex],'materialFiles':[None,None],'materialFileBase':{}}
        check(client.put(api,json=fixture).status_code==200,'Synthetic duplicate-name rows are initialized with legacy empty attachment metadata')
        legacy_bytes=b'EXISTING LEGACY ATTACHMENT'
        legacy=client.post(api+'/attachments',files={'file':('Legacy.ai',legacy_bytes,'application/octet-stream')}).json()['file']
        legacy_state=state();legacy_state.update(materialFiles=[legacy,None],materialFileBase={'__proto__':None,fixture['materialRowIds'][1]:None},richTextBase=legacy_state.get('richText',{'version':1,'fields':{}}))
        check(client.put(api,json=legacy_state).status_code==200,'Existing single-file ticket metadata remains accepted')
        board_before=client.get('/jobticket/corkboard/api').json()
        with sync_playwright() as pw:
            browser=pw.chromium.launch();context=browser.new_context(viewport={'width':1200,'height':1100})
            def guard(route):
                request=route.request
                if not request.url.startswith(base+'/'):
                    external.append(request.url);return route.abort()
                if request.method not in ('GET','HEAD','OPTIONS'):writes.append({'method':request.method,'url':request.url})
                return route.continue_()
            context.route('**/*',guard)
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            def rows():return page.locator('#matBody tr')
            def settled():eventually(lambda:page.evaluate('MaterialAttachments.pendingCount()')==0 and page.locator('#saveStatus').inner_text().startswith('Saved'),'Attachment change did not settle into a current saved revision',page)
            def add(files,index=0):
                with page.expect_file_chooser() as chooser:rows().nth(index).locator('.material-file-attach').click()
                assert chooser.value.is_multiple(),'Add files picker must support multiple selection'
                chooser.value.set_files(files)
            def replace(name,file,keyboard=False):
                button=page.get_by_role('button',name='Replace '+name+' for material 1',exact=True)
                with page.expect_file_chooser() as chooser:
                    button.press('Enter') if keyboard else button.click()
                assert not chooser.value.is_multiple(),'Replace picker must target one existing file'
                chooser.value.set_files(file)
            page.goto(base+'/jobticket/',wait_until='networkidle')
            check(page.get_by_role('button',name='Add files to material 1',exact=True).is_disabled(),'Scratch rows show disabled Add files until a ticket is saved')
            page.goto(base+'/jobticket/FILES01',wait_until='networkidle');page.wait_for_timeout(950)
            check(not writes and page.locator('.material-file-download').first.inner_text()=='Legacy.ai','Loading a legacy attachment creates no writes and retains its filename')
            original=b'%PDF-1.4\nSYNTHETIC FRONT LAYER\n%%EOF';name='Front <draft> layer.pdf';cut=b'SYNTHETIC CUT AI'
            add([upload_file(name,original),upload_file('Cut.ai',cut)])
            eventually(lambda:len(row_files(state()))==3,'Selecting two files must persist both alongside the existing attachment',page);settled()
            saved=state();first=row_files(saved)[1];cut_file=row_files(saved)[2]
            check([file['name'] for file in row_files(saved)]==['Legacy.ai',name,'Cut.ai'],'Multiple selection appends both files without replacing an existing file')
            check(len(set(row_ids(saved)))==3 and len(set(saved['materialRowIds']))==2,'Files and duplicate-name rows keep independent stable identities')
            check([client.get(file['url']).content for file in row_files(saved)]==[legacy_bytes,original,cut],'Every attachment downloads its exact original bytes')
            with page.expect_download() as downloaded:page.get_by_role('link',name=name,exact=True).click()
            download=downloaded.value;download.save_as(OUT/'downloaded.pdf')
            check((OUT/'downloaded.pdf').read_bytes()==original and download.suggested_filename.endswith('layer.pdf'),'Browser download returns the selected file bytes and filename')
            page.locator('.rich-editor[data-rich-key="notes"]').fill('Attachment baseline supports valid row identifiers')
            eventually(lambda:state()['notes']=='Attachment baseline supports valid row identifiers','A later prose edit did not save with attachment baseline',page);settled()
            check(row_ids(state())==row_ids(saved),'A special row identifier and later prose edit retain every file')
            page.reload(wait_until='networkidle')
            check(page.locator('.material-file-download').all_text_contents()==['Legacy.ai',name,'Cut.ai'] and page.locator('.material-file-download b').count()==0,'Reload restores all literal filenames without interpreting markup')
            check(page.get_by_role('button',name='Add files to material 1',exact=True).is_visible(),'Add files stays available after attachments exist')
            add([upload_file('Same-name.ai',b'FIRST SAME NAME'),upload_file('Same-name.ai',b'SECOND SAME NAME')])
            eventually(lambda:len(row_files(state()))==5,'Later multi-selection did not append files',page);settled()
            duplicate_files=row_files(state())[-2:]
            check(duplicate_files[0]['id']!=duplicate_files[1]['id'] and [client.get(file['url']).content for file in duplicate_files]==[b'FIRST SAME NAME',b'SECOND SAME NAME'],'Matching filenames remain separate downloadable attachments')
            before_ids=row_ids(state());replace('Cut.ai',upload_file('Cut-v2.ai',b'UPDATED CUT'))
            eventually(lambda:any(file['name']=='Cut-v2.ai' for file in row_files(state())),'Individual replacement did not save',page);settled()
            after_ids=row_ids(state())
            check(after_ids[:2]==before_ids[:2] and after_ids[3:]==before_ids[3:] and after_ids[2]!=cut_file['id'],'Replacing one file retains all other files and their order')
            check(client.get(cut_file['url']).content==cut,'Replaced original bytes remain retained')
            before_failure=row_ids(state());(root/'fail-upload').touch();replace(name,upload_file('Failed.ai',b'FAIL'))
            eventually(lambda:'failed' in rows().first.locator('.material-file-status').inner_text().lower(),'Failed replacement was not reported',page)
            eventually(lambda:page.evaluate('MaterialAttachments.pendingCount()')==0,'Failed upload remained pending',page)
            check(row_ids(state())==before_failure and page.get_by_role('link',name=name,exact=True).count()==1,'A failed replacement retains every attachment and the original download')
            (root/'fail-upload').unlink();(root/'fail-once-upload').touch()
            add([upload_file('Batch-failed.ai',b'FAIL ONCE'),upload_file('Batch-good.ai',b'GOOD AFTER FAILURE')])
            eventually(lambda:len(row_files(state()))==6,'Batch did not continue to the valid file after a failed upload',page);settled()
            check(row_ids(state())[:5]==before_failure and row_files(state())[-1]['name']=='Batch-good.ai','A mixed-result selection preserves earlier files and saves the later successful file')
            check('Batch-failed.ai' in rows().first.locator('.material-file-status').inner_text() and 'failed' in rows().first.locator('.material-file-status').inner_text().lower(),'A mixed-result selection identifies the failed filename')
            before_oversize=row_ids(state());post_count=sum(item['method']=='POST' for item in writes)
            page.evaluate('''()=>{const file=new File([new ArrayBuffer(104857601)],'Too-large.ai');const dt=new DataTransfer();dt.items.add(file);const input=document.querySelector('.material-file-input');input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}));}''')
            eventually(lambda:'100' in rows().first.locator('.material-file-status').inner_text(),'Oversize selection was not rejected',page)
            check(row_ids(state())==before_oversize and sum(item['method']=='POST' for item in writes)==post_count,'The per-file 100 MB limit rejects an oversized selection before upload and keeps existing files')
            page.get_by_role('button',name='Remove Legacy.ai from material 1',exact=True).click()
            eventually(lambda:len(row_files(state()))==5,'Individual removal did not save',page);settled()
            check(row_ids(state())==before_oversize[1:] and client.get(legacy['url']).content==legacy_bytes,'Removing one file retains all other files, the row and retained bytes')
            add([upload_file('Back-layer.ai',b'BACK AI'),upload_file('Back-proof.pdf',b'BACK PDF')],index=1)
            eventually(lambda:len(row_files(state(),1))==2,'Second row multi-selection did not save',page);settled();second_ids=row_ids(state(),1)
            rows().first.locator('.row-delete').click()
            eventually(lambda:len(state()['materials'])==1,'Material row deletion did not save',page);settled()
            check(state()['materialDetails']==['Back layer'] and row_ids(state())==second_ids,'Deleting a duplicate-name material row keeps all files on the surviving row')
            check(page.get_by_role('button',name='Replace Back-layer.ai for material 1',exact=True).count()==1,'Each file action names its file and follows updated row order')
            replace('Back-layer.ai',upload_file('Keyboard-layer.ai',b'KEYBOARD'),keyboard=True)
            eventually(lambda:row_files(state())[0]['name']=='Keyboard-layer.ai','Keyboard replacement did not save',page);settled()
            check(rows().count()==1 and row_ids(state())[1]==second_ids[1],'Enter activates one-file Replace without adding a material row or changing another file')
            rows().first.locator('.rich-editor[data-rich-key$=":details"]').press('Enter')
            eventually(lambda:len(state()['materials'])==2,'Enter in details did not add a material row',page);settled()
            check(rows().count()==2,'Enter in Material Details still adds the next material row')
            (root/'hold-upload').touch();add([upload_file('Deleted-row.ai',b'DELETED ROW'),upload_file('Never-uploaded.ai',b'NEVER')],index=1)
            eventually(lambda:(root/'upload-held').exists(),'Upload response was not held',page)
            check(page.evaluate("()=>!window.dispatchEvent(new Event('beforeunload',{cancelable:true}))"),'A pending upload batch protects against leaving the ticket')
            pending_posts=sum(item['method']=='POST' for item in writes)
            rows().nth(1).locator('.row-delete').click();(root/'hold-upload').unlink()
            eventually(lambda:len(state()['materials'])==1 and page.evaluate('MaterialAttachments.pendingCount()')==0,'Deleting a pending-upload row did not finish',page);settled()
            check([file['name'] for file in row_files(state())]==['Keyboard-layer.ai','Back-proof.pdf'] and sum(item['method']=='POST' for item in writes)==pending_posts,'Deleting a row cancels the remaining batch and cannot move files onto another row')
            page.reload(wait_until='networkidle');before_render_writes=len(writes);page.wait_for_timeout(950)
            check(len(writes)==before_render_writes and page.locator('.material-file-download').count()==2,'Reloading multiple files triggers no save')
            for width in [1200,390,320]:
                page.set_viewport_size({'width':width,'height':1100})
                check(page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth+1'),f'Attachment rows remain within a {width}px viewport')
                check(all(page.locator('.material-file-download').nth(i).evaluate('(e)=>e.scrollWidth<=e.clientWidth+1') for i in range(2)),f'Each filename remains readable at {width}px')
            page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
            page.set_viewport_size({'width':1200,'height':1100});page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
            page.emulate_media(media='print');page.pdf(path=str(OUT/'attachments-letter.pdf'),format='Letter',print_background=False)
            printed=PdfReader(OUT/'attachments-letter.pdf');text='\n'.join(sheet.extract_text() for sheet in printed.pages)
            uris=[str(annotation.get_object().get('/A',{}).get('/URI','')) for sheet in printed.pages for annotation in sheet.get('/Annots',[])]
            check(not any(uri.startswith(base) for uri in uris),'Print has plain filenames without broken loopback download links')
            check(all(name in text for name in ('Keyboard-layer.ai','Back-proof.pdf')) and not page.locator('.material-file-replace').first.is_visible() and not page.locator('.material-file-attach').first.is_visible(),'Print includes every filename while hiding all attachment editing controls')
            page.emulate_media(media='screen')
            other=context.new_page();other.goto(base+'/jobticket/FILES01',wait_until='networkidle');other.on('pageerror',lambda e:errors.append(str(e)))
            (root/'hold-save').touch();page.locator('.rich-editor[data-rich-key="notes"]').fill('Save held while files upload')
            eventually(lambda:(root/'save-held').exists(),'Form save response was not held',page)
            before_race=row_ids(state());add([upload_file('Current-layer.ai',b'CURRENT LAYER'),upload_file('Current-proof.pdf',b'CURRENT PROOF')])
            eventually(lambda:page.locator('.material-file-download').count()==4,'Concurrent file selection did not display all files',page)
            (root/'hold-save').unlink();eventually(lambda:len(row_files(state()))==4,'A file uploaded during the pending save was lost',page);settled()
            check(row_ids(state())[:2]==before_race and state()['notes']=='Save held while files upload','All files uploaded during an older save persist with the newer edit')
            other.locator('.rich-editor[data-rich-key="notes"]').fill('Stale tab must not erase newer files')
            eventually(lambda:'changed elsewhere' in other.locator('#saveStatus').inner_text(),'Stale save conflict was not displayed',other)
            check(len(row_files(state()))==4 and state()['notes']=='Save held while files upload','A stale browser tab cannot erase a newly added attachment list')
            other.close()
            for name in ['Keyboard-layer.ai','Back-proof.pdf','Current-layer.ai','Current-proof.pdf']:
                page.get_by_role('button',name='Remove '+name+' from material 1',exact=True).press('Enter')
            eventually(lambda:row_files(state())==[],'Removing all references did not save an empty row list',page);settled()
            check(rows().count()==1 and page.locator('.material-file-download').count()==0 and page.locator('.material-file-attach').first.is_visible(),'Removing every file retains the material row and Add files control')
            heights=page.evaluate("()=>[document.querySelector('#matBody tr').getBoundingClientRect().height,document.querySelector('#prodBody tr').getBoundingClientRect().height]")
            check(abs(heights[0]-heights[1])<=1,'A row without files retains compact Production Step height')
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
