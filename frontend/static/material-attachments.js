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
  function filesFrom(value){
    return (Array.isArray(value)?value:value?[value]:[]).map(metadata).filter(Boolean);
  }
  function element(tag,className,text){
    const node=document.createElement(tag);node.className=className;if(text)node.textContent=text;return node;
  }
  function labels(row){
    const number=[...document.querySelectorAll('#matBody tr')].indexOf(row)+1;
    row.querySelector('.material-file-attach').setAttribute('aria-label','Add files to material '+number);
    row.querySelectorAll('.material-file-line').forEach(line=>{
      const name=line.querySelector('.material-file-download').textContent;
      line.querySelector('.material-file-replace').setAttribute('aria-label','Replace '+name+' for material '+number);
      line.querySelector('.material-file-remove').setAttribute('aria-label','Remove '+name+' from material '+number);
    });
  }
  function render(row){
    const uploading=!!row.materialUpload,attach=row.querySelector('.material-file-attach');
    attach.disabled=!boot.saving||uploading;
    attach.title=boot.saving?'Add files (100 MB each)':'Save a ticket before attaching files';
    const list=row.querySelector('.material-file-list');list.replaceChildren();
    row.materialFiles.forEach(file=>{
      const line=element('div','material-file-line'),link=element('a','material-file-download no-print',file.name);
      line.dataset.fileId=file.id;link.href=file.url;link.setAttribute('download',file.name);link.title=file.name;
      const printed=element('span','material-file-print',file.name);
      const replace=element('button','material-file-replace no-print','Replace');replace.type='button';replace.disabled=uploading;
      replace.addEventListener('click',()=>choose(row,file.id));
      const remove=element('button','material-file-remove no-print','Remove');remove.type='button';remove.disabled=uploading;
      remove.addEventListener('click',()=>{
        const index=row.materialFiles.findIndex(value=>value.id===file.id);
        row.materialFiles=row.materialFiles.filter(value=>value.id!==file.id);
        message(row,'');render(row);row.dispatchEvent(new Event('change',{bubbles:true}));
        const next=row.querySelectorAll('.material-file-remove');
        (next[Math.min(index,next.length-1)]||row.querySelector('.material-file-attach')).focus();
      });
      line.append(link,printed,replace,remove);list.append(line);
    });
    labels(row);
  }
  function message(row,text,error=false){
    const status=row.querySelector('.material-file-status');status.hidden=!text;status.textContent=text;status.classList.toggle('is-error',error);
  }
  function choose(row,replaceId=null){
    if(!boot.saving||row.materialUpload)return;
    const input=row.querySelector('.material-file-input');
    row.materialReplaceId=replaceId;input.multiple=!replaceId;input.value='';input.click();
  }
  async function upload(row,files,replaceId){
    if(!files.length||!boot.saving||row.materialUpload)return;
    const generation=(row.materialUploadGeneration||0)+1;row.materialUploadGeneration=generation;
    const controller=new AbortController();row.materialUpload=controller;pending++;
    const failures=[];
    render(row);
    try{
      for(const [index,file] of files.entries()){
        if(controller.signal.aborted||!row.isConnected||row.materialUploadGeneration!==generation)break;
        if(file.size>limit){failures.push(file.name+': exceeds 100 MB.');continue;}
        message(row,'Uploading '+file.name+(files.length>1?' ('+(index+1)+' of '+files.length+')':'')+'…');
        try{
          const body=new FormData();body.append('file',file);
          const response=await fetch(api+'/attachments',{method:'POST',body,signal:controller.signal});
          if(!response.ok)throw Error(response.status===413?'exceeds 100 MB.':'upload failed.');
          const result=await response.json(),fileData=metadata(result.file);
          if(!fileData)throw Error('upload failed.');
          if(controller.signal.aborted||!row.isConnected||row.materialUploadGeneration!==generation)break;
          if(replaceId){
            if(!row.materialFiles.some(value=>value.id===replaceId))break;
            row.materialFiles=row.materialFiles.map(value=>value.id===replaceId?fileData:value);
          }else{
            row.materialFiles=[...row.materialFiles,fileData];
          }
          render(row);row.dispatchEvent(new Event('change',{bubbles:true}));
        }catch(error){
          if(error.name==='AbortError')break;
          failures.push(file.name+': '+(error.message||'upload failed.'));
        }
      }
    }finally{
      pending--;
      if(row.materialUploadGeneration===generation){
        row.materialUpload=null;
        if(row.isConnected){
          render(row);
          message(row,failures.length?failures.join(' ')+' Existing files kept.':'',failures.length>0);
        }
      }
    }
  }
  function initializeRow(row){
    row.materialRowId=newId();row.materialFiles=[];row.materialUpload=null;row.materialReplaceId=null;
    const cell=row.querySelector('.material-details-cell');cell.classList.add('has-attachment-control');
    const input=element('input','material-file-input');input.type='file';input.multiple=true;input.hidden=true;input.tabIndex=-1;
    input.addEventListener('change',()=>{
      const files=[...(input.files||[])],replaceId=row.materialReplaceId;
      row.materialReplaceId=null;input.value='';input.multiple=true;
      upload(row,replaceId?files.slice(0,1):files,replaceId);
    });
    const attach=element('button','material-file-attach no-print','📎');attach.type='button';attach.addEventListener('click',()=>choose(row));
    const list=element('div','material-file-list');
    const status=element('div','material-file-status no-print');status.hidden=true;status.setAttribute('role','status');
    cell.append(input,attach,list,status);render(row);
  }
  function restoreRow(row,rowId,files){
    if(typeof rowId==='string'&&idPattern.test(rowId))row.materialRowId=rowId;
    row.materialFiles=filesFrom(files);render(row);
  }
  function rowState(){
    const rows=[...document.querySelectorAll('#matBody tr')];
    return {materialRowIds:rows.map(row=>row.materialRowId),materialFiles:rows.map(row=>row.materialFiles.map(file=>({...file}))),
      materialFileBase:Object.fromEntries(Object.entries(baseline).map(([id,files])=>[id,[...files]]))};
  }
  function acknowledge(state){
    baseline=Object.create(null);
    (state.materialRowIds||[]).forEach((id,index)=>{baseline[id]=filesFrom((state.materialFiles||[])[index]).map(file=>file.id);});
  }
  function cancel(row){
    row.materialUploadGeneration=(row.materialUploadGeneration||0)+1;
    if(row.materialUpload)row.materialUpload.abort();row.materialUpload=null;
  }
  window.MaterialAttachments={initializeRow,restoreRow,labels,rowState,acknowledge,cancel,pendingCount:()=>pending};
})();
