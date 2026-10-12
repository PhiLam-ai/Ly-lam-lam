/* Compare two validated manual evaluation records without inferring visual quality from morph deltas. */
(function(root){'use strict';
  const CRITERIA=['recognition','symmetry','deformation','transition','repeatability'];
  function compareRecords(inputA,inputB){
    const api=root.AvatarExpressionEvaluationLog;
    if(!api)return {ok:false,reason:'evaluation-api-unavailable'};
    const a=api.parseRecord(inputA),b=api.parseRecord(inputB);
    if(!a.ok)return {ok:false,side:'A',reason:a.reason,details:a};
    if(!b.ok)return {ok:false,side:'B',reason:b.reason,details:b};
    const left=a.record,right=b.record;
    if(left.case_id!==right.case_id)return {ok:false,reason:'case-mismatch',case_a:left.case_id,case_b:right.case_id};
    const criteria=CRITERIA.map(key=>{
      const scoreA=left.scores[key],scoreB=right.scores[key];
      return {key,a:scoreA,b:scoreB,delta:Number.isInteger(scoreA)&&Number.isInteger(scoreB)?scoreB-scoreA:null};
    });
    function average(record){const values=CRITERIA.map(key=>record.scores[key]).filter(Number.isInteger);return values.length?values.reduce((sum,n)=>sum+n,0)/values.length:null;}
    const avgA=average(left),avgB=average(right);
    const snapshotA=left.snapshot,snapshotB=right.snapshot;
    let snapshotComparison=null;
    if(snapshotA&&snapshotB){
      if(snapshotA.asset!==snapshotB.asset)return {ok:false,reason:'asset-mismatch'};
      const names=Object.keys(snapshotA.morph_weights||{});
      const namesB=Object.keys(snapshotB.morph_weights||{});
      if(names.length!==namesB.length||names.some(name=>!Object.prototype.hasOwnProperty.call(snapshotB.morph_weights,name)))return {ok:false,reason:'morph-set-mismatch'};
      const deltas=names.map(name=>({name,a:snapshotA.morph_weights[name],b:snapshotB.morph_weights[name],delta:snapshotB.morph_weights[name]-snapshotA.morph_weights[name]})).filter(row=>row.delta!==0).sort((x,y)=>Math.abs(y.delta)-Math.abs(x.delta)||x.name.localeCompare(y.name));
      snapshotComparison={asset:snapshotA.asset,morphCount:names.length,changedCount:deltas.length,maxAbsDelta:deltas.length?Math.max(...deltas.map(row=>Math.abs(row.delta))):0,differences:deltas};
    }
    return {ok:true,case_id:left.case_id,project_version_a:left.project_version,project_version_b:right.project_version,created_at_a:left.created_at,created_at_b:right.created_at,device_browser_a:left.device_browser,device_browser_b:right.device_browser,reviewer_a:left.reviewer,reviewer_b:right.reviewer,criteria,average_a:avgA,average_b:avgB,average_delta:avgA!==null&&avgB!==null?avgB-avgA:null,scored_count_a:CRITERIA.filter(key=>Number.isInteger(left.scores[key])).length,scored_count_b:CRITERIA.filter(key=>Number.isInteger(right.scores[key])).length,snapshot_comparison:snapshotComparison,observations_a:left.observations,observations_b:right.observations,evidence_a:left.evidence_file,evidence_b:right.evidence_file};
  }
  root.AvatarExpressionEvaluationCompare={CRITERIA,compareRecords};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.AvatarExpressionEvaluationCompare;
})(typeof globalThis!=='undefined'?globalThis:this);
