/* Aggregate validated evaluation-comparison reports; never infer visual quality from scores. */
(function(root){'use strict';
  const SCHEMA='ly-lam-lam-expression-aggregate';
  const CRITERIA=['recognition','symmetry','deformation','transition','repeatability'];
  function aggregateReports(input){
    let reports=input;
    if(typeof input==='string'){try{reports=JSON.parse(input);}catch(_){return {ok:false,reason:'invalid-json'};}}
    if(!Array.isArray(reports)||reports.length===0)return {ok:false,reason:'reports-must-be-nonempty-array'};
    const api=root.AvatarExpressionEvaluationReport;
    if(!api)return {ok:false,reason:'report-api-unavailable'};
    const parsed=[];
    for(let i=0;i<reports.length;i++){const result=api.parseReport(reports[i]);if(!result.ok)return {ok:false,reason:'invalid-report',index:i,details:result};parsed.push(result.report);}
    const groups=new Map();
    for(const report of parsed){if(!groups.has(report.case_id))groups.set(report.case_id,[]);groups.get(report.case_id).push(report);}
    const cases=[...groups.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([case_id,items])=>{
      const criteria=CRITERIA.map(key=>{const deltas=items.map(r=>r.scores.criteria.find(c=>c.key===key)).filter(Boolean).map(c=>c.delta).filter(Number.isFinite);return {key,comparisons:deltas.length,mean_delta:deltas.length?deltas.reduce((s,n)=>s+n,0)/deltas.length:null,improved:deltas.filter(n=>n>0).length,unchanged:deltas.filter(n=>n===0).length,declined:deltas.filter(n=>n<0).length};});
      const deltas=items.map(r=>r.scores.average_delta).filter(Number.isFinite);
      return {case_id,report_count:items.length,project_pairs:items.map(r=>({a:r.project_versions.a,b:r.project_versions.b})),mean_average_delta:deltas.length?deltas.reduce((s,n)=>s+n,0)/deltas.length:null,average_delta_count:deltas.length,criteria};
    });
    return {ok:true,summary:{schema:SCHEMA,version:1,report_count:parsed.length,case_count:cases.length,generated_at:new Date().toISOString(),interpretation:'Aggregated manual review scores only; not an automatic visual-quality judgment.',limitations:['Scores are manually entered and may vary by reviewer.','Reports may use different devices, browsers, lighting, or evidence conditions.','A positive score delta does not independently prove visual improvement.'],cases}};
  }
  root.AvatarExpressionEvaluationAggregate={SCHEMA,CRITERIA,aggregateReports};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.AvatarExpressionEvaluationAggregate;
})(typeof globalThis!=='undefined'?globalThis:this);
