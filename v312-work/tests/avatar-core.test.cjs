'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const Blink = require('../avatar_expression_motion.js');
const Retry = require('../avatar_api_recovery.js');
const Composer = require('../avatar_expression_composer.js');
const Transition = require('../avatar_morph_transition.js');
const Mesh = require('../avatar_mesh_inspector.js');
const Snapshot = require('../avatar_expression_snapshot.js');
const Compare = require('../avatar_expression_compare.js');
const EvaluationLog = require('../avatar_expression_evaluation_log.js');
const EvaluationCompare = require('../avatar_expression_evaluation_compare.js');
const EvaluationReport = require('../avatar_expression_evaluation_report.js');
const EvaluationAggregate = require('../avatar_expression_evaluation_aggregate.js');
const EvidenceAudit = require('../avatar_expression_evidence_audit.js');

test('blink controller: deterministic schedule, close/hold/open, and disabled reset', () => {
  const blink = Blink.createBlinkController({random:()=>0,minInterval:1000,maxInterval:2000,closeMs:100,holdMs:50,openMs:150});
  assert.equal(blink.update(0,true),0);
  assert.equal(blink.update(999,true),0);
  assert.equal(blink.update(1000,true),0);
  assert.equal(blink.update(1050,true),0.5);
  assert.equal(blink.update(1100,true),1);
  assert.equal(blink.update(1150,true),1);
  assert.equal(blink.update(1225,true),0.5);
  assert.equal(blink.update(1300,true),0);
  assert.equal(blink.update(1400,false),0);
  assert.equal(blink.update(1401,true),0);
});

test('blink smoothstep clamps input and remains finite', () => {
  assert.equal(Blink.smoothstep01(-2),0);
  assert.equal(Blink.smoothstep01(2),1);
  assert.equal(Blink.smoothstep01(0.5),0.5);
});

test('retry policy uses bounded exponential backoff and resets after success', () => {
  const policy = Retry.createRetryPolicy({baseDelayMs:100,maxDelayMs:350,factor:2});
  assert.equal(policy.failures,0); assert.equal(policy.delay(),100);
  policy.failure(); assert.equal(policy.delay(),100);
  policy.failure(); assert.equal(policy.delay(),200);
  policy.failure(); assert.equal(policy.delay(),350);
  for(let i=0;i<40;i++) policy.failure();
  assert.ok(policy.failures<=30); assert.equal(policy.delay(),350);
  policy.success(); assert.equal(policy.failures,0); assert.equal(policy.delay(),100);
});

test('expression composer clamps values and handles invalid inputs', () => {
  assert.deepEqual(Composer.composeExpressionWeights(null),{});
  assert.deepEqual(Composer.composeExpressionWeights([1,2]),{});
  const result=Composer.composeExpressionWeights({smile:2,mouth_open:-1,lip_press:0.5,blink_left:NaN});
  assert.equal(result.smile,1); assert.equal(result.mouth_open,0); assert.equal(result.blink_left,0);
});

test('expression composer coordinates competing lip shapes and jaw limits', () => {
  const result=Composer.composeExpressionWeights({lip_fv:0.8,lip_round:0.7,smile:1,cheek_raise:1,mouth_open:0.9,jaw_open:0.8,jaw_hinge:0.7});
  assert.equal(result.lip_fv,0.8); assert.ok(result.lip_round<0.7);
  assert.ok(result.smile<1); assert.ok(result.cheek_raise<1);
  assert.ok(result.jaw_open<=result.mouth_open); assert.ok(result.jaw_hinge<=result.jaw_open);
});

test('procedural blink never overrides a stronger API blink', () => {
  const result=Composer.composeAvatarFrame({blink_left:0.8,blink_right:0.1},0.4);
  assert.equal(result.blink_left,0.8); assert.equal(result.blink_right,0.4);
});

test('morph transition is bounded, smooth, frame-time safe, and resettable', () => {
  const t=Transition.createMorphTransition({timeConstantSeconds:0.1});
  assert.deepEqual(t.update({smile:1},0),{smile:0});
  const first=t.update({smile:1},0.05).smile;
  assert.ok(first>0&&first<1);
  const fast=t.update({smile:1},99).smile;
  assert.ok(fast>first&&fast<1);
  const saturated=t.update({smile:2},0.25).smile;
  assert.ok(saturated>fast&&saturated<1);
  const fading=t.update({},0.25).smile;
  assert.ok(fading>=0&&fading<saturated);
  t.reset({smile:0.3}); assert.equal(t.snapshot().smile,0.3);
});

test('mesh inspector collects meshes and toggles visibility safely', () => {
  const mesh={isMesh:true,name:'face',visible:true};
  const scene={traverse(fn){fn(mesh);fn({isMesh:false});}};
  assert.deepEqual(Mesh.collectMeshEntries(scene),[{node:mesh,name:'face',visible:true}]);
  assert.equal(Mesh.setMeshVisibility(mesh,false),false); assert.equal(mesh.visible,false);
  assert.equal(Mesh.setMeshVisibility(null,true),false);
  assert.deepEqual(Mesh.collectMeshEntries(null),[]);
});

test('camera presets handle all axes, clamp distance, and reject unknown names', () => {
  assert.deepEqual(Mesh.getCameraPreset('front',3,1),{x:0,y:1,z:3});
  assert.deepEqual(Mesh.getCameraPreset('back',3,1),{x:0,y:1,z:-3});
  assert.deepEqual(Mesh.getCameraPreset('left',0,0),{x:-0.1,y:0,z:0});
  assert.deepEqual(Mesh.getCameraPreset('right',3,1),{x:3,y:1,z:0});
  assert.equal(Mesh.getCameraPreset('diagonal',3),null);
});

test('vertex manifest grouping validates rows, deduplicates indices, and sorts', () => {
  const manifest={manifest:'V206 vertex inspection manifest',vertices:[
    {vertex_id:'b',node_index:1,mesh_index:0,primitive_index:0,vertex_index:7},
    {vertex_id:'a',node_index:1,mesh_index:0,primitive_index:0,vertex_index:2},
    {vertex_id:'dup',node_index:1,mesh_index:0,primitive_index:0,vertex_index:7},
    {vertex_id:'bad',node_index:-1,mesh_index:0,primitive_index:0,vertex_index:1}
  ]};
  const groups=Mesh.buildVertexHighlightGroups(manifest);
  assert.equal(groups.length,1); assert.deepEqual(groups[0].vertexIndices,[2,7]);
  assert.deepEqual(Mesh.buildVertexHighlightGroups({}),[]);
});

test('manifest compatibility checks asset identity and animation names', () => {
  const manifest={manifest:'V206 vertex inspection manifest',asset:'./lam-default.glb',animation_names:['Idle','Talk'],vertices:[]};
  assert.equal(Mesh.validateManifestCompatibility(manifest,'https://site.test/lam-default.glb?x=1',[{name:'Talk'},{name:'Idle'}]).ok,true);
  assert.equal(Mesh.validateManifestCompatibility(manifest,'other.glb',[]).reason,'asset-name-mismatch');
  assert.deepEqual(Mesh.validateManifestCompatibility(manifest,'lam-default.glb',[{name:'Idle'}]).missingAnimations,['Talk']);
  assert.equal(Mesh.validateManifestCompatibility({},'lam-default.glb',[]).reason,'invalid-manifest');
});

test('animation seek clamps time and reports invalid clips', () => {
  const clips=[{name:'Idle',duration:2.5}];
  assert.deepEqual(Mesh.resolveAnimationSeek(clips,'Idle',9),{ok:true,clip:clips[0],duration:2.5,time:2.5});
  assert.equal(Mesh.resolveAnimationSeek(clips,'Idle',-1).time,0);
  assert.equal(Mesh.resolveAnimationSeek(clips,'Missing',0).reason,'animation-not-found');
  assert.equal(Mesh.resolveAnimationSeek([], 'Idle',0).reason,'animation-not-found');
});

test('manifest time filter returns only intervals active at selected time', () => {
  const manifest={manifest:'V206 vertex inspection manifest',asset:'lam-default.glb',vertices:[
    {vertex_id:'v1',flagged_intervals:[{animation:'Walk',time_start:1,time_end:2},{animation:'Talk',time_start:3,time_end:4}]},
    {vertex_id:'v2',flagged_intervals:[{animation:'Walk',time_start:2,time_end:3}]}
  ]};
  const result=Mesh.filterManifestAtTime(manifest,'Walk',2);
  assert.equal(result.invalidManifest,false); assert.equal(result.matchedIntervals,2); assert.equal(result.manifest.vertices.length,2);
  assert.equal(Mesh.filterManifestAtTime(manifest,'Talk',3.5).manifest.vertices[0].vertex_id,'v1');
  assert.equal(Mesh.filterManifestAtTime(manifest,'Walk',NaN).invalidManifest,true);
});


test('expression snapshots round-trip bounded weights for the same asset', () => {
  const names=['smile','blink_left','mouth_open'];
  const snap=Snapshot.createSnapshot({smile:0.75,blink_left:2,mouth_open:-1,ignored:1},names,'./lam-default.glb');
  assert.deepEqual(snap,{schema:'ly-lam-lam-expression-snapshot',version:1,asset:'./lam-default.glb',morph_weights:{smile:0.75,blink_left:1,mouth_open:0}});
  assert.deepEqual(Snapshot.parseSnapshot(JSON.stringify(snap),names,'./lam-default.glb'),{ok:true,weights:{smile:0.75,blink_left:1,mouth_open:0}});
});

test('expression snapshots reject invalid JSON, schemas, asset mismatch, unknown morphs, and non-finite values', () => {
  const names=['smile','mouth_open'];
  assert.equal(Snapshot.parseSnapshot('{oops',names).reason,'invalid-json');
  assert.equal(Snapshot.parseSnapshot('{}',names).reason,'invalid-schema');
  const base=Snapshot.createSnapshot({smile:0.4},names);
  assert.equal(Snapshot.parseSnapshot({...base,asset:'other.glb'},names).reason,'asset-mismatch');
  assert.equal(Snapshot.parseSnapshot({...base,morph_weights:{smile:0.4,not_real:1}},names).reason,'unknown-morphs');
  assert.equal(Snapshot.parseSnapshot({...base,morph_weights:{smile:'not-a-number'}},names).reason,'invalid-weight');
});


test('expression comparison reports deterministic changed weights and aggregate deltas', () => {
  const names=['smile','blink_left','mouth_open'];
  const a=Snapshot.createSnapshot({smile:0.2,blink_left:0.1,mouth_open:0.4},names);
  const b=Snapshot.createSnapshot({smile:0.8,blink_left:0.1,mouth_open:0.2},names);
  const result=Compare.compareSnapshots(JSON.stringify(a),JSON.stringify(b),names);
  assert.equal(result.ok,true); assert.equal(result.morphCount,3); assert.equal(result.changedCount,2);
  assert.ok(Math.abs(result.maxAbsDelta-0.6)<1e-12);
  assert.ok(Math.abs(result.meanAbsDelta-(0.8/3))<1e-12);
  assert.equal(result.differences[0].name,'smile'); assert.equal(result.differences[0].delta,0.6000000000000001);
});

test('expression comparison identifies which snapshot is invalid and rejects incompatible assets', () => {
  const names=['smile']; const good=Snapshot.createSnapshot({smile:0.3},names);
  assert.deepEqual(Compare.compareSnapshots('{bad',JSON.stringify(good),names),{ok:false,side:'A',reason:'invalid-json',details:{ok:false,reason:'invalid-json'}});
  const other=Snapshot.createSnapshot({smile:0.3},names,'other.glb');
  assert.equal(Compare.compareSnapshots(JSON.stringify(good),JSON.stringify(other),names).reason,'asset-mismatch');
  assert.equal(Compare.compareSnapshots(JSON.stringify(good),'{bad',names).side,'B');
});

test('identical expression snapshots produce zero difference', () => {
  const names=['smile','blink_left']; const snap=JSON.stringify(Snapshot.createSnapshot({smile:0.4},names));
  const result=Compare.compareSnapshots(snap,snap,names);
  assert.equal(result.ok,true); assert.equal(result.changedCount,0); assert.equal(result.maxAbsDelta,0); assert.equal(result.meanAbsDelta,0);
});


test('evaluation log creates a bounded, round-trippable manual review record', () => {
  const snapshot=Snapshot.createSnapshot({smile:0.5},['smile']);
  const record=EvaluationLog.createRecord({created_at:'2026-10-10T00:00:00.000Z',project_version:'V229',case_id:'smile-soft',device_browser:'iPhone · Safari',scores:{recognition:4,symmetry:3,deformation:'N/A',transition:2,repeatability:3},observations:'Khóe miệng hơi lệch.',evidence_file:'smile-soft.png',snapshot});
  assert.equal(record.schema,'ly-lam-lam-expression-evaluation');
  assert.equal(record.scores.deformation,'N/A');
  const parsed=EvaluationLog.parseRecord(JSON.stringify(record));
  assert.equal(parsed.ok,true); assert.equal(parsed.record.case_id,'smile-soft');
  assert.deepEqual(parsed.record.snapshot,snapshot);
});

test('evaluation log requires case, version, device, and all valid scores', () => {
  assert.throws(()=>EvaluationLog.createRecord({case_id:'smile',project_version:'V229',device_browser:'Safari',scores:{}}),/Invalid score/);
  assert.throws(()=>EvaluationLog.createRecord({project_version:'V229',device_browser:'Safari',scores:{recognition:1,symmetry:1,deformation:1,transition:1,repeatability:1}}),/case_id/);
  assert.throws(()=>EvaluationLog.createRecord({case_id:'smile',project_version:'V229',device_browser:'Safari',scores:{recognition:5,symmetry:1,deformation:1,transition:1,repeatability:1}}),/Invalid score/);
});

test('evaluation log rejects malformed snapshots and invalid JSON records', () => {
  const scores={recognition:1,symmetry:1,deformation:1,transition:1,repeatability:1};
  assert.throws(()=>EvaluationLog.createRecord({case_id:'smile',project_version:'V229',device_browser:'Safari',scores,snapshot:{schema:'wrong'}}),/valid expression snapshot/);
  assert.deepEqual(EvaluationLog.parseRecord('{bad'),{ok:false,reason:'invalid-json'});
  assert.equal(EvaluationLog.parseRecord({schema:'wrong',version:1}).reason,'invalid-schema');
});


test('evaluation comparison reports per-criterion and mean score changes for the same case', () => {
  const snapshotA=Snapshot.createSnapshot({smile:0.2,blink_left:0},['smile','blink_left']);
  const snapshotB=Snapshot.createSnapshot({smile:0.7,blink_left:0.3},['smile','blink_left']);
  const common={case_id:'smile-soft',device_browser:'Safari',scores:{recognition:2,symmetry:'N/A',deformation:3,transition:2,repeatability:4}};
  const a=EvaluationLog.createRecord({...common,project_version:'V229',created_at:'2026-10-10T00:00:00Z',scores:{...common.scores,recognition:2,transition:2},snapshot:snapshotA});
  const b=EvaluationLog.createRecord({...common,project_version:'V230',created_at:'2026-10-10T01:00:00Z',scores:{...common.scores,recognition:4,transition:3},snapshot:snapshotB});
  const result=EvaluationCompare.compareRecords(a,b);
  assert.equal(result.ok,true); assert.equal(result.case_id,'smile-soft');
  assert.equal(result.criteria.find(row=>row.key==='recognition').delta,2);
  assert.equal(result.criteria.find(row=>row.key==='symmetry').delta,null);
  assert.equal(result.average_a,2.75); assert.equal(result.average_b,3.5); assert.equal(result.average_delta,0.75);
  assert.equal(result.snapshot_comparison.changedCount,2);
  assert.equal(result.snapshot_comparison.differences[0].name,'smile');
});

test('evaluation comparison rejects invalid records, different cases, assets, and morph sets', () => {
  assert.equal(EvaluationCompare.compareRecords('{bad','{}').side,'A');
  const scores={recognition:1,symmetry:1,deformation:1,transition:1,repeatability:1};
  const make=(case_id,asset='lam-default.glb',weights={smile:0.2})=>EvaluationLog.createRecord({case_id,project_version:'V230',device_browser:'Safari',scores,snapshot:Snapshot.createSnapshot(weights,Object.keys(weights),asset)});
  assert.equal(EvaluationCompare.compareRecords(make('smile'),make('blink')).reason,'case-mismatch');
  assert.equal(EvaluationCompare.compareRecords(make('smile'),make('smile','other.glb')).reason,'asset-mismatch');
  assert.equal(EvaluationCompare.compareRecords(make('smile'),make('smile','lam-default.glb',{other:0.2})).reason,'morph-set-mismatch');
});

test('evaluation comparison handles N/A-only records without fabricating averages', () => {
  const record=EvaluationLog.createRecord({case_id:'neutral',project_version:'V230',device_browser:'Safari',scores:{recognition:'N/A',symmetry:'N/A',deformation:'N/A',transition:'N/A',repeatability:'N/A'}});
  const result=EvaluationCompare.compareRecords(record,record);
  assert.equal(result.ok,true); assert.equal(result.average_a,null); assert.equal(result.average_delta,null); assert.equal(result.scored_count_a,0);
});


test('V231 evaluation report exports a portable, caveated JSON comparison', () => {
  const scoresA={recognition:2,symmetry:2,deformation:'N/A',transition:3,repeatability:2};
  const scoresB={recognition:3,symmetry:3,deformation:3,transition:3,repeatability:3};
  const a=EvaluationLog.createRecord({created_at:'2026-10-09T00:00:00.000Z',project_version:'V229',case_id:'smile-soft',device_browser:'Safari iPhone',reviewer:'A',scores:scoresA,observations:'Môi hơi lệch',evidence_file:'a.png'});
  const b=EvaluationLog.createRecord({created_at:'2026-10-10T00:00:00.000Z',project_version:'V231',case_id:'smile-soft',device_browser:'Chrome desktop',reviewer:'B',scores:scoresB,observations:'Đã cân đối hơn',evidence_file:''});
  const compared=EvaluationCompare.compareRecords(a,b);
  assert.equal(compared.ok,true);
  const report=EvaluationReport.createReport(compared,'2026-10-10T12:00:00.000Z');
  assert.equal(report.schema,'ly-lam-lam-expression-comparison-report');
  assert.equal(report.project_versions.a,'V229');
  assert.equal(report.project_versions.b,'V231');
  assert.ok(report.limitations.some(item=>item.includes('differs')));
  assert.ok(report.limitations.some(item=>item.includes('evidence')));
  assert.equal(EvaluationReport.parseReport(JSON.stringify(report)).ok,true);
});

test('V231 evaluation report rejects failed comparisons and malformed or incomplete reports', () => {
  assert.throws(()=>EvaluationReport.createReport({ok:false}),/successful evaluation comparison/);
  assert.deepEqual(EvaluationReport.parseReport('{bad'),{ok:false,reason:'invalid-json'});
  assert.equal(EvaluationReport.parseReport({schema:'wrong',version:1}).reason,'invalid-schema');
  const valid={schema:'ly-lam-lam-expression-comparison-report',version:1,case_id:'smile',project_versions:{a:'V1',b:'V2'},scores:{criteria:[]},limitations:[]};
  assert.equal(EvaluationReport.parseReport(valid).reason,'invalid-report');
  const rowKeys=['recognition','symmetry','deformation','transition','repeatability'];
  valid.scores.criteria=rowKeys.map(key=>({key,a:2,b:3,delta:1}));
  assert.equal(EvaluationReport.parseReport(valid).ok,true);
  valid.scores.criteria[0].b=5;
  assert.equal(EvaluationReport.parseReport(valid).reason,'invalid-criteria');
});

test('V231 diagnostics integrates JSON report creation and validation with comparison provenance', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  for(const id of ['evaluation-report-tools','evaluation-report-create','evaluation-report-json','evaluation-report-validate','evaluation-report-result']) assert.match(html,new RegExp(`id=["']${id}["']`),`missing ${id}`);
  assert.match(html,/avatar_expression_evaluation_report\.js/);
  assert.match(html,/lastEvaluationComparison=result/);
  assert.match(html,/evaluationReportApi\.createReport/);
  assert.match(html,/evaluationReportApi\.parseReport/);
  const report=fs.readFileSync(path.join(root,'avatar_expression_evaluation_report.js'),'utf8');
  assert.match(report,/manual-review-report/); assert.match(report,/visual quality/); assert.match(report,/device_browser_a/);
});


test('V232 aggregates validated reports by case and summarizes score delta directions', () => {
  const makeReport=(case_id,delta)=>({schema:'ly-lam-lam-expression-comparison-report',version:1,generated_at:'2026-10-10T00:00:00Z',status:'manual-review-report',case_id,project_versions:{a:'V230',b:'V231'},devices:{a:'Safari',b:'Safari'},reviewers:{a:'A',b:'A'},scores:{average_a:2,average_b:2+delta,average_delta:delta,scored_count_a:5,scored_count_b:5,criteria:['recognition','symmetry','deformation','transition','repeatability'].map((key,i)=>({key,a:2,b:2+(i===0?delta:0),delta:i===0?delta:0}))},observations:{a:'',b:''},evidence_files:{a:'a.png',b:'b.png'},snapshot_comparison:null,limitations:[]});
  const result=EvaluationAggregate.aggregateReports([makeReport('smile-soft',1),makeReport('smile-soft',-1),makeReport('blink-left',0)]);
  assert.equal(result.ok,true);assert.equal(result.summary.report_count,3);assert.equal(result.summary.case_count,2);
  const smile=result.summary.cases.find(row=>row.case_id==='smile-soft');assert.equal(smile.report_count,2);assert.equal(smile.mean_average_delta,0);
  const recognition=smile.criteria.find(row=>row.key==='recognition');assert.equal(recognition.improved,1);assert.equal(recognition.declined,1);assert.equal(recognition.unchanged,0);
  assert.match(result.summary.interpretation,/manual review/);
});

test('V232 aggregation rejects invalid JSON, empty arrays and invalid member reports', () => {
  assert.equal(EvaluationAggregate.aggregateReports('{bad').reason,'invalid-json');
  assert.equal(EvaluationAggregate.aggregateReports([]).reason,'reports-must-be-nonempty-array');
  const result=EvaluationAggregate.aggregateReports([{schema:'wrong',version:1}]);assert.equal(result.ok,false);assert.equal(result.index,0);
});

test('V232 diagnostics provides local multi-report aggregation controls', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  for(const id of ['evaluation-aggregate-tools','evaluation-aggregate-input','evaluation-aggregate-run','evaluation-aggregate-output','evaluation-aggregate-result'])assert.match(html,new RegExp(`id=["']${id}["']`));
  assert.match(html,/avatar_expression_evaluation_aggregate\.js/);assert.match(html,/evaluationAggregateApi\.aggregateReports/);
});


test('V233 evidence audit matches exact basenames and flags missing or ambiguous references', () => {
  const makeReport=(case_id,a,b)=>({schema:'ly-lam-lam-expression-comparison-report',version:1,case_id,project_versions:{a:'V231',b:'V233'},scores:{criteria:['recognition','symmetry','deformation','transition','repeatability'].map(key=>({key,a:2,b:3,delta:1}))},limitations:[],evidence_files:{a,b}});
  const result=EvidenceAudit.auditReports([makeReport('smile','old/smile.png','new.png'),makeReport('blink','dup.png','missing.png')],['smile.png','new.png','dup.png','dup.png']);
  assert.equal(result.ok,true);
  assert.deepEqual(result.audit.evidence_reference_totals,{matched:2,missing:1,not_recorded:0,ambiguous:1});
  assert.equal(result.audit.reports[0].evidence[0].status,'matched');
  assert.equal(result.audit.reports[1].evidence[0].status,'ambiguous-duplicate-filename');
  assert.equal(result.audit.reports[1].evidence[1].status,'missing');
  assert.match(result.audit.interpretation,/does not open/);
});

test('V233 evidence audit marks absent evidence and rejects malformed report collections', () => {
  const report={schema:'ly-lam-lam-expression-comparison-report',version:1,case_id:'neutral',project_versions:{a:'V1',b:'V2'},scores:{criteria:['recognition','symmetry','deformation','transition','repeatability'].map(key=>({key,a:'N/A',b:'N/A',delta:null}))},limitations:[],evidence_files:{a:'',b:null}};
  const result=EvidenceAudit.auditReports([report],[]);
  assert.equal(result.ok,true); assert.equal(result.audit.evidence_reference_totals.not_recorded,2);
  assert.equal(EvidenceAudit.auditReports('{bad',[]).reason,'invalid-json');
  assert.equal(EvidenceAudit.auditReports([],[]).reason,'reports-must-be-nonempty-array');
  assert.equal(EvidenceAudit.auditReports([{schema:'bad'}],[]).reason,'invalid-report');
});

test('V233 diagnostics wires local evidence file selection and audit controls', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  for(const id of ['evaluation-evidence-audit-tools','evaluation-evidence-audit-input','evaluation-evidence-files','evaluation-evidence-audit-run','evaluation-evidence-audit-output','evaluation-evidence-audit-result']) assert.match(html,new RegExp(`id=["']${id}["']`));
  assert.match(html,/avatar_expression_evidence_audit\.js/); assert.match(html,/evidenceAuditApi\.auditReports/);
  assert.match(html,/does not prove|không xác nhận ảnh đúng phiên bản/i);
});

test('V234 evidence file manifest records SHA-256, metadata, and duplicate byte content', async () => {
  const files=[
    {name:'captures/a.png',size:4,type:'image/png',arrayBuffer:async()=>new ArrayBuffer(4)},
    {name:'captures/b.png',size:4,type:'image/png',arrayBuffer:async()=>new ArrayBuffer(4)},
    {name:'captures/c.png',size:3,type:'image/jpeg',arrayBuffer:async()=>new ArrayBuffer(3)}
  ];
  const hashes={'a.png':'a'.repeat(64),'b.png':'a'.repeat(64),'c.png':'b'.repeat(64)};
  const result=await EvidenceAudit.createFileManifest(files,async(file)=>hashes[file.name.split('/').pop()]);
  assert.equal(result.ok,true);
  assert.equal(result.manifest.schema,'ly-lam-lam-expression-file-manifest');
  assert.equal(result.manifest.file_count,3);
  assert.equal(result.manifest.unique_content_count,2);
  assert.equal(result.manifest.files[0].filename,'a.png');
  assert.equal(result.manifest.files[0].size_bytes,4);
  assert.equal(result.manifest.files[0].sha256,'a'.repeat(64));
  assert.match(result.manifest.interpretation,/do not prove image authenticity/i);
});

test('V234 joins unique evidence references to byte hashes and keeps missing or duplicate names cautious', async () => {
  const makeReport=(case_id,a,b)=>({schema:'ly-lam-lam-expression-comparison-report',version:1,case_id,project_versions:{a:'V232',b:'V234'},scores:{criteria:['recognition','symmetry','deformation','transition','repeatability'].map(key=>({key,a:2,b:3,delta:1}))},limitations:[],evidence_files:{a,b}});
  const files=[
    {name:'old.png',size:10,type:'image/png',arrayBuffer:async()=>new ArrayBuffer(10)},
    {name:'new.png',size:20,type:'image/png',arrayBuffer:async()=>new ArrayBuffer(20)},
    {name:'dup.png',size:5,type:'image/png',arrayBuffer:async()=>new ArrayBuffer(5)},
    {name:'dup.png',size:6,type:'image/png',arrayBuffer:async()=>new ArrayBuffer(6)}
  ];
  const result=await EvidenceAudit.auditReportsWithManifest([makeReport('smile','old.png','new.png'),makeReport('blink','dup.png','absent.png')],files,async(file)=>String(file.size).padStart(64,'0'));
  assert.equal(result.ok,true);
  assert.equal(result.audit.reports[0].evidence[0].sha256,'10'.padStart(64,'0'));
  assert.equal(result.audit.reports[0].evidence[1].size_bytes,20);
  assert.equal(result.audit.reports[1].evidence[0].status,'ambiguous-duplicate-filename');
  assert.equal(result.audit.reports[1].evidence[0].sha256,undefined);
  assert.equal(result.audit.reports[1].evidence[1].status,'missing');
  assert.match(result.audit.limitations.at(-1),/does not authenticate/i);
});

test('V234 evidence hashing reports unavailable crypto and invalid file metadata safely', async () => {
  const file={name:'x.png',size:1,type:'image/png',arrayBuffer:async()=>new ArrayBuffer(1)};
  assert.equal((await EvidenceAudit.createFileManifest([],async()=> 'a'.repeat(64))).reason,'files-must-be-nonempty-array');
  assert.equal((await EvidenceAudit.createFileManifest([file],async()=> 'not-a-hash')).reason,'invalid-sha256');
  assert.equal((await EvidenceAudit.createFileManifest([file],async()=>{throw new Error('read failed');})).reason,'file-read-or-hash-failed');
  assert.equal((await EvidenceAudit.createFileManifest([file],null)).ok,typeof globalThis.crypto!=='undefined'&&!!globalThis.crypto.subtle);
});

test('V234 diagnostics clearly exposes local SHA-256 manifest and limitations', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/SHA-256/); assert.match(html,/auditReportsWithManifest/); assert.match(html,/không xác minh nội dung hình ảnh/i);
  const module=fs.readFileSync(path.join(root,'avatar_expression_evidence_audit.js'),'utf8');
  assert.match(module,/ly-lam-lam-expression-file-manifest/); assert.match(module,/subtle\.digest\('SHA-256'/i);
});


test('V295 GLB load failure preserves status controls and exposes retry diagnostics', () => {
  const module = fs.readFileSync(path.join(root, 'module.mjs'), 'utf8');
  const callback = module.match(/\},undefined,e=>\{([\s\S]*?)\}\);/);
  assert.ok(callback, 'GLTFLoader must retain an explicit error callback');
  assert.match(callback[1], /window\.__lyLamBootFailed=true/);
  assert.match(callback[1], /clearTimeout\(window\.__lyLamBootTimer\)/);
  assert.match(callback[1], /statusMessage\.textContent=/);
  assert.match(callback[1], /window\.__lyLamShowRetry\(\)/);
  assert.doesNotMatch(callback[1], /status\.textContent=/, 'replacing the status container would remove retry/switch controls');
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /id="retry-startup"/);
  assert.match(html, /id="switch-three-mode"/);
});


test('V299 local app-module errors do not trigger an irrelevant Three.js CDN fallback', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /window\.__lyLamIsLocalStartupFailure = \(event, message = ''\) =>/);
  assert.match(html, /url\.origin === location\.origin/);
  assert.match(html, /if \(window\.__lyLamIsLocalStartupFailure\(event, message\)\)/);
  assert.match(html, /window\.__lyLamIsLocalStartupFailure\(\{ filename: '' \}/);
  assert.match(html, /Không tự đổi CDN vì việc đó không sửa lỗi mã ứng dụng/);
});

test('V298 WebGL context restoration hides stale startup recovery controls after avatar is ready', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const listener = html.match(/addEventListener\('webglcontextrestored',[\s\S]*?\}\);\n/);
  assert.ok(listener, 'renderer must handle WebGL context restoration');
  assert.match(listener[0], /if\(viewerReady\)/);
  assert.match(listener[0], /querySelector\('#retry-startup'\)/);
  assert.match(listener[0], /querySelector\('#switch-three-mode'\)/);
  assert.match(listener[0], /if\(retry\)retry\.hidden=true/);
  assert.match(listener[0], /if\(modeButton\)modeButton\.hidden=true/);
  assert.match(listener[0], /đã được khôi phục/i);
});
