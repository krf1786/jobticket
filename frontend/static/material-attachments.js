/* Per-material attachments; files follow durable row IDs, never table positions. */
(()=>{
  'use strict';
  const limit=104857600,boot=window.__TICKET__||{},prefix=boot.prefix||'/jobticket';
  const api=prefix+'/api/'+encodeURIComponent(boot.jobId||'');
  let pending=0,baseline=Object.create(null);
  const idPattern=/^[A-Za-z0-9_-]{1,128}$/;
  const newId=()=>crypto.randomUUID().replaceAll('-','');
  function metadata(file){
    if(!file||!/^[0-9a-f]{32}$/.test(file.id)||typeof file.name!=='string'||!Number.isSafeInteger(file.size)||file.size<0||file.size>limit)return null;
    return {id:file.id,name:file.name,size:file.size,url:api+'/attachments/'+file.id};
  }
  function element(tag,className,text){
    const node=document.createElement(tag);node.className=className;if(text)node.textContent=text;return node;
  }
  function labels(row){
    const number=[...document.querySelectorAll('#matBody tr')].indexOf(row)+1;
    row.querySelector('.material-file-attach').setAttribute('aria-label','Attach file to material '+number);
    row.querySelector('.material-file-replace').setAttribute('aria-label','Replace file for material '+number);
    row.querySelector('.material-file-remove').setAttribute('aria-label','Remove file from material '+number);
  }
  function render(row){
    const file=row.materialFile,uploading=!!row.materialUpload;
    const attach=row.querySelector('.material-file-attach'),line=row.querySelector('.material-file-line'),link=row.querySelector('.material-file-download');
    attach.hidden=!!file;attach.disabled=!boot.saving||uploading;
    attach.title=boot.saving?'Attach file (100 MB max)':'Save a ticket before attaching files';
    line.hidden=!file;
    if(file){link.textContent=file.name;link.href=file.url;link.setAttribute('download',file.name);link.title=file.name;}
    else {link.textContent='';link.removeAttribute('href');link.removeAttribute('download');}
    row.querySelector('.material-file-print').textContent=file?file.name:'';
    for(const button of row.querySelectorAll('.material-file-replace,.material-file-remove'))button.disabled=uploading;
    labels(row);
  }
  function message(row,text,error=false){
    const status=row.querySelector('.material-file-status');status.hidden=!text;status.textContent=text;status.classList.toggle('is-error',error);
  }
  function choose(row){
    if(!boot.saving||row.materialUpload)return;
    const input=row.querySelector('.material-file-input');input.value='';input.click();
  }
  async function upload(row,file){
    if(!file||!boot.saving)return;
    if(file.size>limit){message(row,'File exceeds 100 MB; existing attachment kept.',true);return;}
    const generation=(row.materialUploadGeneration||0)+1;row.materialUploadGeneration=generation;
    if(row.materialUpload)row.materialUpload.abort();
    const controller=new AbortController();row.materialUpload=controller;pending++;
    render(row);message(row,'Uploading '+file.name+'…');
    try{
      const body=new FormData();body.append('file',file);
      const response=await fetch(api+'/attachments',{method:'POST',body,signal:controller.signal});
      if(!response.ok)throw Error(response.status===413?'File exceeds 100 MB; existing attachment kept.':'Upload failed; existing attachment kept.');
      const result=await response.json(),fileData=metadata(result.file);
      if(!fileData)throw Error('Upload failed; existing attachment kept.');
      if(!row.isConnected||row.materialUploadGeneration!==generation)return;
      row.materialFile=fileData;message(row,'');render(row);
      row.dispatchEvent(new Event('change',{bubbles:true}));
    }catch(error){
      if(row.isConnected&&row.materialUploadGeneration===generation&&error.name!=='AbortError')message(row,error.message||'Upload failed; existing attachment kept.',true);
    }finally{
      pending--;
      if(row.materialUploadGeneration===generation){row.materialUpload=null;if(row.isConnected)render(row);}
    }
  }
  function initializeRow(row){
    row.materialRowId=newId();row.materialFile=null;row.materialUpload=null;
    const cell=row.querySelector('.material-details-cell');cell.classList.add('has-attachment-control');
    const input=element('input','material-file-input');input.type='file';input.hidden=true;input.tabIndex=-1;
    input.addEventListener('change',()=>{const file=input.files&&input.files[0];input.value='';upload(row,file);});
    const attach=element('button','material-file-attach no-print','📎');attach.type='button';attach.addEventListener('click',()=>choose(row));
    const line=element('div','material-file-line'),link=element('a','material-file-download no-print'),printed=element('span','material-file-print');line.hidden=true;
    const replace=element('button','material-file-replace no-print','Replace');replace.type='button';replace.addEventListener('click',()=>choose(row));
    const remove=element('button','material-file-remove no-print','Remove');remove.type='button';remove.addEventListener('click',()=>{
      row.materialFile=null;message(row,'');render(row);row.dispatchEvent(new Event('change',{bubbles:true}));
    });
    line.append(link,printed,replace,remove);
    const status=element('div','material-file-status no-print');status.hidden=true;status.setAttribute('role','status');
    cell.append(input,attach,line,status);render(row);
  }
  function restoreRow(row,rowId,file){
    if(typeof rowId==='string'&&idPattern.test(rowId))row.materialRowId=rowId;
    row.materialFile=metadata(file);render(row);
  }
  function rowState(){
    const rows=[...document.querySelectorAll('#matBody tr')];
    return {materialRowIds:rows.map(row=>row.materialRowId),materialFiles:rows.map(row=>row.materialFile),materialFileBase:{...baseline}};
  }
  function acknowledge(state){
    baseline=Object.create(null);
    (state.materialRowIds||[]).forEach((id,index)=>{baseline[id]=(state.materialFiles[index]||{}).id||null;});
  }
  function cancel(row){
    row.materialUploadGeneration=(row.materialUploadGeneration||0)+1;
    if(row.materialUpload)row.materialUpload.abort();row.materialUpload=null;
  }
  window.MaterialAttachments={initializeRow,restoreRow,labels,rowState,acknowledge,cancel,pendingCount:()=>pending};
})();
