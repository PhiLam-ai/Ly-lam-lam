/* Local, schema-validated manual expression evaluation records. */
(function(root){'use strict';
  const SCHEMA='ly-lam-lam-expression-evaluation';
  const CRITERIA=['recognition','symmetry','deformation','transition','repeatability'];
  const ALLOWED_SCORES=new Set([0,1,2,3,4,'N/A']);
  function cleanText(value,max=500){return typeof value==='string'?value.trim().slice(0,max):'';}
  function normalizeScore(value){if(value==='N/A')return 'N/A';if(typeof value==='string'&&value.trim()!=='')value=Number(value);return Number.isInteger(value)&&value>=0&&value<=4?value:null;}
  function createRecord(input){
    if(!input||typeof input!=='object'||Array.isArray(input))throw new TypeError('Evaluation input must be an object');
    const caseId=cleanText(input.case_id,100), version=cleanText(input.project_version,40), device=cleanText(input.device_browser,160);
    if(!caseId)throw new TypeError('case_id is required');
    if(!version)throw new TypeError('project_version is required');
    if(!device)throw new TypeError('device_browser is required');
    const scores={};
    for(const key of CRITERIA){const score=normalizeScore(input.scores&&input.scores[key]);if(score===null)throw new TypeError(`Invalid score: ${key}`);scores[key]=score;}
    const snapshot=input.snapshot===undefined||input.snapshot===null?null:input.snapshot;
    if(snapshot!==null&&(!snapshot||typeof snapshot!=='object'||Array.isArray(snapshot)||snapshot.schema!=='ly-lam-lam-expression-snapshot'||snapshot.version!==1||typeof snapshot.morph_weights!=='object'||!snapshot.morph_weights||Array.isArray(snapshot.morph_weights)))throw new TypeError('snapshot must be a valid expression snapshot');
    return {schema:SCHEMA,version:1,created_at:cleanText(input.created_at,40),project_version:version,case_id:caseId,device_browser:device,reviewer:cleanText(input.reviewer,120),scores,observations:cleanText(input.observations,2000),evidence_file:cleanText(input.evidence_file,240),snapshot};
  }
  function parseRecord(input){let data=input;try{if(typeof input==='string')data=JSON.parse(input);}catch(_){return {ok:false,reason:'invalid-json'};}
    if(!data||typeof data!=='object'||Array.isArray(data)||data.schema!==SCHEMA||data.version!==1)return {ok:false,reason:'invalid-schema'};
    try{return {ok:true,record:createRecord(data)};}catch(error){return {ok:false,reason:'invalid-record',message:error.message};}
  }
  root.AvatarExpressionEvaluationLog={SCHEMA,CRITERIA,ALLOWED_SCORES,createRecord,parseRecord,normalizeScore};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.AvatarExpressionEvaluationLog;
})(typeof globalThis!=='undefined'?globalThis:this);
