/* Build a portable JSON report from a successful evaluation comparison. */
(function(root){'use strict';
  const SCHEMA='ly-lam-lam-expression-comparison-report';
  function createReport(comparison,generatedAt){
    if(!comparison||typeof comparison!=='object'||comparison.ok!==true||typeof comparison.case_id!=='string'||!Array.isArray(comparison.criteria))throw new TypeError('A successful evaluation comparison is required');
    const criteria=['recognition','symmetry','deformation','transition','repeatability'];
    if(comparison.criteria.length!==criteria.length||criteria.some(key=>!comparison.criteria.some(row=>row&&row.key===key)))throw new TypeError('Comparison criteria are incomplete');
    const warnings=['Scores are manually entered and do not constitute automatic visual assessment.','Morph-weight differences are numerical only and do not prove improved visual quality.'];
    if(!comparison.device_browser_a||!comparison.device_browser_b)warnings.push('Device/browser metadata is missing; visual comparisons may not be comparable.');
    else if(comparison.device_browser_a!==comparison.device_browser_b)warnings.push('Device/browser metadata differs; treat score and image comparisons cautiously.');
    if(!comparison.evidence_a||!comparison.evidence_b)warnings.push('One or both evidence filenames are missing; visual improvement is not independently evidenced by this report.');
    return {schema:SCHEMA,version:1,generated_at:typeof generatedAt==='string'&&generatedAt?generatedAt:new Date().toISOString(),status:'manual-review-report',case_id:comparison.case_id,project_versions:{a:comparison.project_version_a,b:comparison.project_version_b},devices:{a:comparison.device_browser_a||'',b:comparison.device_browser_b||''},reviewers:{a:comparison.reviewer_a||'',b:comparison.reviewer_b||''},scores:{average_a:comparison.average_a,average_b:comparison.average_b,average_delta:comparison.average_delta,scored_count_a:comparison.scored_count_a,scored_count_b:comparison.scored_count_b,criteria:comparison.criteria.map(row=>({key:row.key,a:row.a,b:row.b,delta:row.delta}))},observations:{a:comparison.observations_a||'',b:comparison.observations_b||''},evidence_files:{a:comparison.evidence_a||'',b:comparison.evidence_b||''},snapshot_comparison:comparison.snapshot_comparison||null,limitations:warnings};
  }
  function parseReport(input){let data=input;try{if(typeof input==='string')data=JSON.parse(input);}catch(_){return {ok:false,reason:'invalid-json'};}
    if(!data||typeof data!=='object'||Array.isArray(data)||data.schema!==SCHEMA||data.version!==1)return {ok:false,reason:'invalid-schema'};
    if(typeof data.case_id!=='string'||!data.case_id.trim()||!data.project_versions||typeof data.project_versions.a!=='string'||typeof data.project_versions.b!=='string'||!data.scores||!Array.isArray(data.scores.criteria)||data.scores.criteria.length!==5||!Array.isArray(data.limitations)||data.limitations.some(item=>typeof item!=='string'))return {ok:false,reason:'invalid-report'};
    const expected=['recognition','symmetry','deformation','transition','repeatability'];
    if(expected.some(key=>!data.scores.criteria.some(row=>row&&row.key===key&&(row.a==='N/A'||Number.isInteger(row.a)&&row.a>=0&&row.a<=4)&&(row.b==='N/A'||Number.isInteger(row.b)&&row.b>=0&&row.b<=4)&&(row.delta===null||Number.isInteger(row.delta)&&row.delta>=-4&&row.delta<=4))))return {ok:false,reason:'invalid-criteria'};
    return {ok:true,report:data};
  }
  root.AvatarExpressionEvaluationReport={SCHEMA,createReport,parseReport};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.AvatarExpressionEvaluationReport;
})(typeof globalThis!=='undefined'?globalThis:this);
