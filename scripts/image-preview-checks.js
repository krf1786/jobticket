// Synthetic-only UI verification; the preview server never persists data.
async (page) => {
  const origin = 'http://127.0.0.1:18765';
  const checks = [], errors = [], blocked = [], api = [];
  const svg = (w, h) => `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><rect width="${w}" height="${h}" fill="#f1f5f9"/><rect x="${w*.1}" y="${h*.1}" width="${w*.8}" height="${h*.8}" rx="30" fill="#0e7490"/><circle cx="${w*.5}" cy="${h*.5}" r="${Math.min(w,h)*.2}" fill="#fbbf24"/><text x="${w*.5}" y="${h*.88}" text-anchor="middle" font-size="${Math.min(w,h)*.06}" fill="#fff">SYNTHETIC IMAGE PREVIEW</text></svg>`;
  const source = 'data:image/svg+xml,' + encodeURIComponent(svg(1800,1200));
  const check = (ok, label) => { if (!ok) throw new Error(label); checks.push(label); };
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/*', async route => {
    const req=route.request(),url=new URL(req.url());
    if (url.origin!==origin) { blocked.push(req.url()); return route.abort(); }
    if (url.pathname.startsWith('/jobticket/api/')) { api.push({method:req.method(),path:url.pathname}); return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true})}); }
    if (url.pathname==='/jobticket/DEMO01') {
      const response=await route.fetch();
      const html=(await response.text()).replace(/window\.__TICKET__ = (.*?);<\/script>/s, (_,raw) => {
        const boot=JSON.parse(raw); boot.state.image=source;
        return 'window.__TICKET__ = '+JSON.stringify(boot).replace(/</g,'\\u003c')+';</script>';
      });
      return route.fulfill({response,body:html});
    }
    return route.continue();
  });
  const viewer=page.locator('#imageViewer'),trigger=page.locator('#imagePreviewButton');
  const open = async () => { await trigger.click(); await page.waitForFunction(()=>imageViewer.open && imageViewerImage.complete && imageViewerImage.naturalWidth>0); };
  const closed = async () => { await page.waitForFunction(()=>!imageViewer.open && !document.body.classList.contains('image-viewing')); };
  const fits = () => page.evaluate(()=>{
    const s=imageViewerStage.getBoundingClientRect(),i=imageViewerImage.getBoundingClientRect(),d=imageViewer.getBoundingClientRect();
    return i.width>0 && i.height>0 && i.left>=s.left && i.right<=s.right+1 && i.top>=s.top && i.bottom<=s.bottom+1 && d.left>=0 && d.right<=innerWidth && d.top>=0 && d.bottom<=innerHeight;
  });
  await page.goto(origin+'/jobticket/');
  check(!await trigger.isVisible(), 'Empty box has no preview trigger');
  const [chooser]=await Promise.all([page.waitForEvent('filechooser'),page.locator('#imgBox').click()]);
  await chooser.setFiles({name:'synthetic-landscape.svg',mimeType:'image/svg+xml',buffer:Buffer.from(svg(1800,1200))});
  await page.waitForFunction(()=>imgPreview.complete && imgPreview.naturalWidth===1800);
  check(await trigger.isVisible(), 'Empty box still uploads scratch image');
  let fileDialogs=0;page.on('filechooser',()=>fileDialogs++);
  const before=await page.locator('#imgPreview').getAttribute('src');
  await open();
  check(await fits(),'Landscape image fits desktop viewport without cropping');
  check(fileDialogs===0,'Image click opens viewer without opening upload picker');
  check(await page.evaluate(()=>imageViewer.matches(':modal') && document.body.classList.contains('image-viewing')),'Viewer is modal and locks background scrolling');
  check(await page.getByRole('button',{name:'Close image preview'}).evaluate(e=>e===document.activeElement),'Close receives initial keyboard focus');
  await page.keyboard.press('Shift+Tab');
  check(await page.locator('#imageViewerZoom').evaluate(e=>e===document.activeElement),'Shift+Tab moves between viewer controls');
  await page.getByRole('button',{name:'Actual size',exact:true}).click();
  check(await page.locator('#imageViewerImage').evaluate(e=>Math.abs(e.getBoundingClientRect().width-1800)<1 && Math.abs(e.getBoundingClientRect().height-1200)<1),'Actual-size mode displays original dimensions');
  await page.locator('#imageViewerStage').focus();
  await page.keyboard.press('ArrowRight');await page.keyboard.press('ArrowDown');
  await page.waitForFunction(()=>imageViewerStage.scrollLeft>0 && imageViewerStage.scrollTop>0);
  check(await page.locator('#imageViewerStage').evaluate(e=>e===document.activeElement),'Image scroll area is reachable and scrolls by keyboard');
  await page.locator('#imageViewerStage').evaluate(e=>e.scrollTo(400,300));
  check(await page.locator('#imageViewerStage').evaluate(e=>e.scrollLeft>0 && e.scrollTop>0),'Actual-size image scrolls to inspect details');
  await page.getByRole('button',{name:'Fit to screen',exact:true}).click();
  check(await fits(),'Fit-to-screen restores contained view');
  await page.keyboard.press('Escape');await closed();
  check(await trigger.evaluate(e=>e===document.activeElement),'Escape closes and restores focus to image');
  check(await page.locator('#imageViewerImage').getAttribute('src')===null,'Closing clears enlarged image source');
  await trigger.press('Enter');check(await viewer.evaluate(e=>e.open),'Enter opens preview');
  await page.getByRole('button',{name:'Close image preview'}).click();await closed();
  await trigger.press('Space');check(await viewer.evaluate(e=>e.open),'Space opens preview');
  await page.mouse.click(2,2);await closed();check(!await viewer.isVisible(),'Backdrop click dismisses preview');
  for (const width of [760,390,320]) {
    await page.setViewportSize({width,height:800});await open();
    check(await fits(),`Landscape fits ${width}px viewport`);
    check(await page.getByRole('button',{name:'Close image preview'}).isVisible(),`Close is accessible at ${width}px`);
    if(width===390) await page.screenshot({path:'output/playwright/image-preview-mobile.png'});
    await page.keyboard.press('Escape');await closed();
  }
  await page.setViewportSize({width:1200,height:1000});await open();
  await page.screenshot({path:'output/playwright/image-preview-desktop.png'});
  await page.emulateMedia({media:'print'});
  check(!await viewer.isVisible() && await page.locator('#imgPreview').isVisible(),'Print hides overlay and keeps ticket reference image');
  check(await trigger.evaluate(e=>getComputedStyle(e).outlineStyle)==='none','Print excludes keyboard focus outline');
  await page.waitForFunction(()=>!document.getElementById('toast').classList.contains('show'));
  await page.pdf({path:'output/playwright/image-preview-print.pdf',format:'Letter',printBackground:true});
  check(await viewer.evaluate(e=>!e.open) && !await page.locator('body').evaluate(e=>e.classList.contains('image-viewing')),'Printing closes viewer and unlocks page');
  await page.emulateMedia({media:'screen'});
  check(before===await page.locator('#imgPreview').getAttribute('src'),'Viewing and printing preserve original ticket image');
  const [change]=await Promise.all([page.waitForEvent('filechooser'),page.getByRole('button',{name:'Change image'}).press('Enter')]);
  check(!await viewer.evaluate(e=>e.open),'Keyboard Change opens picker without opening viewer');
  await change.setFiles({name:'synthetic-portrait.svg',mimeType:'image/svg+xml',buffer:Buffer.from(svg(900,1800))});
  await page.waitForFunction(()=>imgPreview.complete && imgPreview.naturalHeight===1800);await open();
  check(await fits(),'Replacement portrait image fits desktop');
  await page.setViewportSize({width:390,height:844});check(await fits(),'Portrait image fits after mobile resize');
  await page.keyboard.press('Escape');await closed();
  await page.getByRole('button',{name:'Remove image'}).click();
  check(!await trigger.isVisible() && await page.locator('#imgPlaceholder').isVisible(),'Removal restores empty upload box');
  check(api.length===0,'Scratch preview interactions send no API requests');

  await page.goto(origin+'/jobticket/DEMO01');
  await page.waitForFunction(()=>imgPreview.complete && imgPreview.naturalWidth===1800);
  await page.waitForTimeout(950);
  await open();
  check(await page.locator('#imageViewerImage').getAttribute('src')===source,'Saved image preview uses restored original source');
  await page.getByRole('button',{name:'Actual size',exact:true}).click();
  await page.keyboard.press('Escape');await closed();await open();
  check(await page.locator('#imageViewerZoom').textContent()==='Actual size','Reopening resets view to fit screen');
  await page.keyboard.press('Escape');await closed();
  await page.waitForTimeout(950);
  check(api.length===0,'Saved image opening/zoom/closing cause no autosave/upload/push');
  check(errors.length===0 && blocked.length===0,'No browser errors or external requests');
  return {passed:checks.length,checks,pageErrors:errors,blockedExternalRequests:blocked,apiRequests:api};
}
