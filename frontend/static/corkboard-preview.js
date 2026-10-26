/* Read-only visual export for the shared JPlak corkboard. No form/save events. */
(()=>{
  'use strict';
  if(window.parent===window)return;
  const allowedOrigin=origin=>origin==='https://jplak-ticket-corkboard.krf1786.chatgpt.site'||origin==='null'||origin===location.origin||/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin);
  const assets=new Map();
  function dataURL(url){
    const resolved=new URL(url,location.href);
    if(resolved.protocol==='data:')return Promise.resolve(resolved.href);
    if(resolved.origin!==location.origin)return Promise.reject(Error('Preview asset must belong to this ticket service'));
    if(!assets.has(resolved.href))assets.set(resolved.href,fetch(resolved.href).then(response=>{if(!response.ok)throw Error('Preview asset unavailable');return response.blob();}).then(blob=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(blob);})).catch(error=>{assets.delete(resolved.href);throw error;}));
    return assets.get(resolved.href);
  }
  async function snapshot(){
    if(document.readyState!=='complete')await new Promise(resolve=>window.addEventListener('load',resolve,{once:true}));
    await document.fonts.ready;
    const page=document.querySelector('.page,.sheet');
    if(!page)throw Error('Ticket page unavailable');
    const copy=page.cloneNode(true),originals=page.querySelectorAll('input,textarea,select'),copies=copy.querySelectorAll('input,textarea,select');
    originals.forEach((field,index)=>{
      const twin=copies[index];
      if(field.tagName==='TEXTAREA')twin.textContent=field.value;
      else if(field.tagName==='SELECT')[...twin.options].forEach((option,i)=>option.toggleAttribute('selected',field.options[i].selected));
      else {twin.setAttribute('value',field.value);twin.toggleAttribute('checked',field.checked);}
    });
    copy.querySelectorAll('script,noscript,iframe,object,embed,dialog').forEach(node=>node.remove());
    for(const node of [copy,...copy.querySelectorAll('*')])for(const attr of [...node.attributes])if(/^on/i.test(attr.name))node.removeAttribute(attr.name);
    await Promise.all([...copy.querySelectorAll('img')].map(async img=>{if(img.getAttribute('src'))img.src=await dataURL(img.src);img.removeAttribute('srcset');}));
    // Freeze the responsive rules selected by the original iframe viewport.
    // An SVG image has a narrower viewport and must not reflow the ticket.
    const activeRules=rules=>[...rules].map(rule=>rule.type===CSSRule.MEDIA_RULE?(matchMedia(rule.conditionText).matches?activeRules(rule.cssRules):''):rule.cssText).join('\n');
    let css=[...document.styleSheets].map(sheet=>activeRules(sheet.cssRules)).join('\n');
    const urls=[...new Set([...css.matchAll(/url\(["']?([^"')]+)["']?\)/g)].map(match=>match[1]))];
    for(const url of urls){const embedded=await dataURL(url);css=css.split(url).join(embedded);}
    css+='\nhtml,body{margin:0!important;background:transparent!important}.page{margin:0!important;box-shadow:none!important}*{animation:none!important;transition:none!important}';
    const ns='http://www.w3.org/2000/svg',xhtml='http://www.w3.org/1999/xhtml';
    const svg=document.createElementNS(ns,'svg');svg.setAttribute('width','816');svg.setAttribute('height','1056');svg.setAttribute('viewBox','0 0 816 1056');
    const foreign=document.createElementNS(ns,'foreignObject');foreign.setAttribute('width','816');foreign.setAttribute('height','1056');
    const wrap=document.createElementNS(xhtml,'body'),style=document.createElementNS(xhtml,'style');style.textContent=css;wrap.append(style,copy);foreign.append(wrap);svg.append(foreign);
    return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(new XMLSerializer().serializeToString(svg));
  }
  let pending=null;
  window.addEventListener('message',async event=>{
    if(event.source!==window.parent||!allowedOrigin(event.origin)||event.data?.type!=='jplak:preview-request'||typeof event.data.requestId!=='string'||event.data.requestId.length>100)return;
    const destination=event.origin==='null'?'*':event.origin;
    try{
      pending ||= snapshot().finally(()=>{pending=null;});
      const image=await pending;
      event.source.postMessage({type:'jplak:preview-response',requestId:event.data.requestId,jobId:window.__TICKET__?.jobId||null,image},destination);
    }catch{
      event.source.postMessage({type:'jplak:preview-response',requestId:event.data.requestId,error:true},destination);
    }
  });
})();
