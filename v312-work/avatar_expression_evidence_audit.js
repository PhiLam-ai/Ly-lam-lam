/* Audit evidence filename references and create a local SHA-256 file manifest. */
(function(root){'use strict';
  const SCHEMA='ly-lam-lam-expression-evidence-audit';
  const MANIFEST_SCHEMA='ly-lam-lam-expression-file-manifest';
  function basename(value){return String(value||'').trim().replace(/\\/g,'/').split('/').pop();}
  function auditReports(input, selectedFiles){
    let reports=input;
    if(typeof input==='string'){try{reports=JSON.parse(input);}catch(_){return {ok:false,reason:'invalid-json'};}}
    if(!Array.isArray(reports)||reports.length===0)return {ok:false,reason:'reports-must-be-nonempty-array'};
    const api=root.AvatarExpressionEvaluationReport;
    if(!api)return {ok:false,reason:'report-api-unavailable'};
    const files=Array.isArray(selectedFiles)?selectedFiles.map(basename).filter(Boolean):[];
    const counts=new Map();for(const name of files)counts.set(name,(counts.get(name)||0)+1);
    const rows=[];
    for(let i=0;i<reports.length;i++){
      const parsed=api.parseReport(reports[i]);
      if(!parsed.ok)return {ok:false,reason:'invalid-report',index:i,details:parsed};
      const report=parsed.report;
      const evidence=['a','b'].map(side=>{
        const reference=basename(report.evidence_files&&report.evidence_files[side]);
        if(!reference)return {side,reference:'',status:'not-recorded',matches:0};
        const matches=counts.get(reference)||0;
        return {side,reference,status:matches===1?'matched':matches===0?'missing':'ambiguous-duplicate-filename',matches};
      });
      rows.push({case_id:report.case_id,project_versions:report.project_versions,evidence,matched:evidence.filter(x=>x.status==='matched').length,missing:evidence.filter(x=>x.status==='missing').length,not_recorded:evidence.filter(x=>x.status==='not-recorded').length,ambiguous:evidence.filter(x=>x.status==='ambiguous-duplicate-filename').length});
    }
    const totals=rows.reduce((acc,row)=>{for(const key of ['matched','missing','not_recorded','ambiguous'])acc[key]+=row[key];return acc;},{matched:0,missing:0,not_recorded:0,ambiguous:0});
    return {ok:true,audit:{schema:SCHEMA,version:1,generated_at:new Date().toISOString(),selected_file_count:files.length,unique_filename_count:counts.size,report_count:rows.length,evidence_reference_totals:totals,reports:rows,interpretation:'Checks filename references only. It does not open, inspect, authenticate, or compare image contents.',limitations:['A matching filename does not prove that the file depicts the stated expression or belongs to the stated version.','Files are compared by basename and exact case-sensitive filename.','Select all relevant evidence files in this browser session; files are not uploaded or saved by this tool.']}};
  }
  async function createFileManifest(selectedFiles, hashFile){
    if(!Array.isArray(selectedFiles)||selectedFiles.length===0)return {ok:false,reason:'files-must-be-nonempty-array'};
    const digest=hashFile||(async file=>{
      if(!root.crypto||!root.crypto.subtle||typeof root.crypto.subtle.digest!=='function')throw new Error('sha256-unavailable');
      const bytes=await file.arrayBuffer();
      const hash=await root.crypto.subtle.digest('SHA-256',bytes);
      return Array.from(new Uint8Array(hash),byte=>byte.toString(16).padStart(2,'0')).join('');
    });
    const entries=[];
    try{
      for(let index=0;index<selectedFiles.length;index++){
        const file=selectedFiles[index];
        if(!file||typeof file.name!=='string'||!file.name.trim()||typeof file.arrayBuffer!=='function')return {ok:false,reason:'invalid-file-object',index};
        const sha256=await digest(file);
        if(typeof sha256!=='string'||!/^[a-f0-9]{64}$/i.test(sha256))return {ok:false,reason:'invalid-sha256',index};
        entries.push({index,filename:basename(file.name),size_bytes:Number.isFinite(file.size)&&file.size>=0?file.size:null,mime_type:typeof file.type==='string'?file.type:'',sha256:sha256.toLowerCase()});
      }
    }catch(error){return {ok:false,reason:error&&error.message==='sha256-unavailable'?'sha256-unavailable':'file-read-or-hash-failed'};}
    const digestCounts=new Map();for(const entry of entries)digestCounts.set(entry.sha256,(digestCounts.get(entry.sha256)||0)+1);
    return {ok:true,manifest:{schema:MANIFEST_SCHEMA,version:1,generated_at:new Date().toISOString(),algorithm:'SHA-256',file_count:entries.length,unique_content_count:digestCounts.size,files:entries,interpretation:'Hashes identify the exact bytes selected at audit time; they do not prove image authenticity, capture conditions, or that an image depicts the claimed expression.',limitations:['A hash proves byte-level identity only when independently recomputed from a trusted copy.','Filename and MIME type are user-agent supplied metadata and are not proof of content.','Files are read locally in this browser session and are not uploaded or persisted by this tool.']}};
  }
  async function auditReportsWithManifest(input, selectedFiles, hashFile){
    const audit=auditReports(input,Array.isArray(selectedFiles)?selectedFiles.map(file=>file&&file.name):[]);
    if(!audit.ok)return audit;
    if(!Array.isArray(selectedFiles)||selectedFiles.length===0)return {ok:false,reason:'files-must-be-nonempty-array'};
    const result=await createFileManifest(selectedFiles,hashFile);
    if(!result.ok)return result;
    const manifest=result.manifest;
    const byName=new Map();for(const file of manifest.files){if(!byName.has(file.filename))byName.set(file.filename,[]);byName.get(file.filename).push(file);}
    for(const row of audit.audit.reports)for(const item of row.evidence){
      if(item.status==='matched'){
        const match=(byName.get(item.reference)||[])[0];
        item.file_manifest_index=match.index;item.sha256=match.sha256;item.size_bytes=match.size_bytes;item.mime_type=match.mime_type;
      }
    }
    audit.audit.file_manifest=manifest;
    audit.audit.interpretation='Checks report filenames and computes SHA-256 for selected file bytes locally. Does not inspect image pixels or verify that evidence depicts the claimed expression/version.';
    audit.audit.limitations.push('SHA-256 identifies file bytes but does not authenticate the source or establish visual correctness.');
    return audit;
  }
  root.AvatarExpressionEvidenceAudit={SCHEMA,MANIFEST_SCHEMA,auditReports,createFileManifest,auditReportsWithManifest};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.AvatarExpressionEvidenceAudit;
})(typeof globalThis!=='undefined'?globalThis:this);
