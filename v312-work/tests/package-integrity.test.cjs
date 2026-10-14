'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const cp = require('node:child_process');
const root = path.resolve(__dirname, '..');


test('V297 closes the stylesheet before the import map and document body', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  const styleOpen=html.indexOf('<style>');
  const styleClose=html.indexOf('</style>',styleOpen);
  const importMapScript=html.indexOf('<script>',styleOpen);
  const headClose=html.indexOf('</head>');
  const bodyOpen=html.indexOf('<body>');
  assert.ok(styleOpen>=0,'stylesheet opening tag exists');
  assert.ok(styleClose>styleOpen,'stylesheet has a closing tag');
  assert.ok(importMapScript>styleClose,'import-map script is outside the stylesheet');
  assert.ok(headClose>importMapScript,'head closes after the import-map script');
  assert.ok(bodyOpen>headClose,'body starts after the head');
  assert.equal((html.match(/<style>/g)||[]).length,(html.match(/<\/style>/g)||[]).length,'style tags are balanced');
});


test('V309 defaults to bundled Three.js locally and keeps explicit pinned CDN overrides', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /const mode=new URLSearchParams\(location\.search\)\.get\('three'\);const local=mode==='local'\|\|mode===null;/, 'omitted mode and explicit local mode must both select bundled assets');
  assert.match(html, /const base=local\?'\.\/vendor\/three\/'\:mode==='unpkg'\?'https:\/\/unpkg\.com\/three@0\.160\.0\/'\:'https:\/\/cdn\.jsdelivr\.net\/npm\/three@0\.160\.0\//, 'default path must use bundled vendor assets while preserving pinned CDN overrides');
  assert.match(html, /thư viện nội bộ \(mặc định\)/, 'diagnostics must describe the actual default');
  assert.match(html, /currentParam === 'cdn' \? 'cdn' : 'local'/, 'recovery switch must treat an omitted mode as local');
  for (const asset of ['vendor/three/build/three.module.js', 'vendor/three/examples/jsm/loaders/GLTFLoader.js', 'vendor/three/examples/jsm/controls/OrbitControls.js']) {
    assert.ok(fs.existsSync(path.join(root, asset)), `bundled module exists: ${asset}`);
  }
});


test('V305 includes a Windows double-click startup helper that gates launch on verification', () => {
  const helper=fs.readFileSync(path.join(root,'START-LAM-LAM-WINDOWS.bat'),'utf8');
  assert.match(helper,/node tools\\verify-startup\.cjs/i);
  assert.match(helper,/if errorlevel 1/i);
  assert.match(helper,/node tools\\start-preview\.cjs --local-three/i);
  assert.match(helper,/Ctrl\+C/i);
});

test('V304 provides a cross-platform one-command startup verification gate', () => {
  const script=fs.readFileSync(path.join(root,'tools/verify-startup.cjs'),'utf8');
  assert.match(script,/startup-preflight\.cjs/);
  assert.match(script,/vendor-module-integrity\.cjs/);
  assert.match(script,/--test/);
  assert.match(script,/static-http-smoke\.cjs/);
  assert.match(script,/chưa xác minh WebGL\/GPU/i);
});

test('GLB header and chunks are structurally valid', () => {
  const data=fs.readFileSync(path.join(root,'lam-default.glb'));
  assert.ok(data.length>=20);
  assert.equal(data.readUInt32LE(0),0x46546c67,'GLB magic');
  assert.equal(data.readUInt32LE(4),2,'GLB version');
  assert.equal(data.readUInt32LE(8),data.length,'declared file length');
  let offset=12, json=null, binCount=0;
  while(offset<data.length){
    assert.ok(offset+8<=data.length,'chunk header fits');
    const length=data.readUInt32LE(offset), type=data.readUInt32LE(offset+4); offset+=8;
    assert.ok(length>=0&&offset+length<=data.length,'chunk fits file');
    if(type===0x4e4f534a) json=JSON.parse(data.subarray(offset,offset+length).toString('utf8').replace(/[\u0000\u0020]+$/g,''));
    if(type===0x004e4942) binCount++;
    offset+=length;
  }
  assert.equal(offset,data.length,'chunks end at EOF');
  assert.ok(json,'JSON chunk exists'); assert.equal(json.asset.version,'2.0');
  assert.ok(json.nodes.length>0); assert.ok(json.meshes.length>0); assert.ok(binCount>=1);
  const morphs=new Set(json.meshes.flatMap(m=>m.extras?.targetNames||[]));
  for(const name of ['smile','blink_left','blink_right','mouth_open','jaw_open','jaw_hinge','brow_raise','cheek_raise','lip_press','lip_fv','lip_round','tongue_tip']) assert.ok(morphs.has(name),`missing morph ${name}`);
  assert.ok(Array.isArray(json.animations));
});

test('HTML points to the bundled GLB and uses opt-in diagnostics', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/targetUrl='\.\/lam-default\.glb'/);
  assert.match(html,/get\('diagnostics'\)==='1'/);
  assert.match(html,/avatar_expression_motion\.js/);
  assert.match(html,/avatar_mesh_inspector\.js/);
  assert.match(html,/avatar_expression_snapshot\.js/);
  assert.match(html,/avatar_expression_compare\.js/);
  for (const id of ['compare-tools','compare-json-a','compare-json-b','compare-run','compare-result']) assert.match(html,new RegExp(`id=[\"']${id}[\"']`));
});


test('V235 keeps the normal launch path light and reports startup failures', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/window\.__lyLamBootTimer\s*=\s*window\.setTimeout/);
  assert.match(html,/window\.__lyLamAppBooted\s*=\s*true/);
  assert.match(html,/Ứng dụng chưa tải xong mô hình sau 15 giây/);
  assert.match(html,/const diagnosticsRequested=new URLSearchParams\(location\.search\)\.get\('diagnostics'\)==='1'/);
  assert.match(html,/if\(diagnosticsRequested\)\{\s*await Promise\.all\(\[/);
  assert.match(html,/import\('\.\/avatar_expression_snapshot\.js'\)/);
  assert.match(html,/import\('\.\/avatar_expression_evidence_audit\.js'\)/);
  assert.match(html,/if\(diagnosticsEnabled\)globalThis\.AvatarMeshInspector\.clearVertexHighlights/);
});

test('mobile preview exposes accessible camera, zoom, and help controls', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  for (const id of ['quick-controls','view-face','view-full','zoom-in','zoom-out','view-reset','help-toggle','help']) {
    assert.match(html,new RegExp(`id=[\"']${id}[\"']`),`missing mobile control ${id}`);
  }
  assert.match(html,/aria-label=\"Điều khiển avatar\"/);
  assert.match(html,/aria-expanded/);
  assert.match(html,/function setQuickView\(/);
  assert.match(html,/function zoomBy\(/);
});


test('mobile viewport adapts to iOS safe areas and dynamic browser height', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/viewport-fit=cover/);
  assert.match(html,/height:100%;height:100dvh/);
  assert.match(html,/env\(safe-area-inset-top\)/);
  assert.match(html,/env\(safe-area-inset-left\)/);
  assert.match(html,/grid-template-columns:repeat\(3,minmax\(0,1fr\)\)/);
});

test('help and diagnostics panels are positioned below the two-row mobile toolbar', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/#help\{[^}]*top:calc\(max\(10px, env\(safe-area-inset-top\)\) \+ 100px\)/);
  assert.match(html,/#diagnostics\{[^}]*top:calc\(max\(10px, env\(safe-area-inset-top\)\) \+ 100px\)/);
  assert.match(html,/max-height:calc\(100dvh - 140px\)/);
});


test('renderer resizes with visual viewport and caps pixel ratio for mobile stability', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/Math\.min\(window\.devicePixelRatio\|\|1,2\)/);
  assert.match(html,/function resizeRenderer\(\)/);
  assert.match(html,/visualViewport\?\.addEventListener\('resize',resizeRenderer\)/);
  assert.match(html,/camera\.aspect=width\/height/);
});

test('render loop bounds frame delta and reports WebGL context recovery', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/Math\.min\(Math\.max\(\(now-last\)\/1000,0\),0\.05\)/);
  assert.match(html,/webglcontextlost/);
  assert.match(html,/webglcontextrestored/);
  assert.match(html,/Đồ họa 3D đã được khôi phục/);
});

test('GLB inventory matches the documented mesh, geometry, skin, and animation counts', () => {
  const data=fs.readFileSync(path.join(root,'lam-default.glb'));
  let offset=12, json=null;
  while(offset<data.length){const length=data.readUInt32LE(offset),type=data.readUInt32LE(offset+4);offset+=8;if(type===0x4e4f534a)json=JSON.parse(data.subarray(offset,offset+length).toString('utf8').replace(/[\u0000\u0020]+$/g,''));offset+=length;}
  const accessors=json.accessors;
  const vertices=json.meshes.reduce((sum,m)=>sum+m.primitives.reduce((n,p)=>n+(p.attributes.POSITION===undefined?0:accessors[p.attributes.POSITION].count),0),0);
  const indices=json.meshes.reduce((sum,m)=>sum+m.primitives.reduce((n,p)=>n+(p.indices===undefined?0:accessors[p.indices].count),0),0);
  assert.equal(json.meshes.length,85);
  assert.equal(vertices,8036);
  assert.equal(indices,33804);
  assert.equal(json.skins.length,1);
  assert.equal(json.skins[0].joints.length,17);
  assert.equal(json.animations.length,6);
  assert.equal(json.materials.length,4);
  assert.equal((json.images||[]).length,0);
});

test('model audit report documents what metadata proves and what still needs visual inspection', () => {
  const report=fs.readFileSync(path.join(root,'MODEL-AUDIT-VI.txt'),'utf8');
  for(const phrase of ['8.036 đỉnh','11.268 tam giác','85 mesh','17 khớp','6 animation','Không có texture ảnh nhúng','Chưa thể kết luận chất lượng hình ảnh']) assert.ok(report.includes(phrase),`missing audit note: ${phrase}`);
});


test('diagnostic mode initializes mobile toolbar before accessing it and provides continuous morph sliders', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  const toolbarDeclaration=html.indexOf("const quickControls=document.querySelector('#quick-controls')");
  const diagnosticBranch=html.indexOf('if(diagnosticsEnabled){diagnostics.style.display=');
  assert.ok(toolbarDeclaration>=0&&toolbarDeclaration<diagnosticBranch,'toolbar must be initialized before diagnostics branch');
  assert.match(html,/Điều chỉnh từng morph \(0–1\)/);
  assert.match(html,/input\.type='range';input\.min='0';input\.max='1';input\.step='0\.05'/);
  assert.match(html,/input\.setAttribute\('aria-label',`Mức morph \${name}`\)/);
  assert.match(html,/function setDebugWeights\(weights\)/);
  assert.match(html,/syncMorphControls\(debugWeights\)/);
});


test('GLB morph targets have nonzero POSITION deltas on expected meshes', () => {
  const data=fs.readFileSync(path.join(root,'lam-default.glb'));
  let offset=12, json=null, binary=null;
  while(offset<data.length){
    const length=data.readUInt32LE(offset),type=data.readUInt32LE(offset+4);offset+=8;
    const chunk=data.subarray(offset,offset+length);offset+=length;
    if(type===0x4e4f534a)json=JSON.parse(chunk.toString('utf8').replace(/[\u0000\u0020]+$/g,''));
    if(type===0x004e4942)binary=chunk;
  }
  assert.ok(json&&binary,'GLB JSON and BIN chunks exist');
  const active=new Map();
  for(let meshIndex=0;meshIndex<json.meshes.length;meshIndex++){
    const mesh=json.meshes[meshIndex], names=mesh.extras?.targetNames||[];
    for(const primitive of mesh.primitives||[]){
      for(let targetIndex=0;targetIndex<(primitive.targets||[]).length;targetIndex++){
        const name=names[targetIndex], accessorIndex=primitive.targets[targetIndex].POSITION;
        if(!name||accessorIndex===undefined)continue;
        const accessor=json.accessors[accessorIndex], view=json.bufferViews[accessor.bufferView];
        assert.equal(accessor.componentType,5126,`${name} POSITION deltas are float32`);
        assert.equal(accessor.type,'VEC3',`${name} POSITION deltas are VEC3`);
        const start=(view.byteOffset||0)+(accessor.byteOffset||0),stride=view.byteStride||12;
        let changed=0,maxDelta=0;
        for(let i=0;i<accessor.count;i++){
          const x=binary.readFloatLE(start+i*stride),y=binary.readFloatLE(start+i*stride+4),z=binary.readFloatLE(start+i*stride+8);
          const magnitude=Math.hypot(x,y,z);
          if(magnitude>1e-8)changed++;
          maxDelta=Math.max(maxDelta,magnitude);
        }
        if(!active.has(name))active.set(name,[]);
        if(changed)active.get(name).push({mesh:mesh.name||`mesh-${meshIndex}`,changed,count:accessor.count,maxDelta});
      }
    }
  }
  const expected={
    smile:['mouth'],blink_left:['left_eye'],blink_right:['right_eye'],mouth_open:['mouth'],
    brow_raise:['left_brow','right_brow'],jaw_open:['mouth','chin'],jaw_hinge:['mouth','chin'],
    cheek_raise:['mouth','chin'],lip_press:['mouth'],lip_fv:['mouth'],lip_round:['mouth'],tongue_tip:['mouth']
  };
  for(const [name,meshNames] of Object.entries(expected)){
    const rows=active.get(name)||[];
    assert.ok(rows.length>0,`${name} must contain a nonzero position delta`);
    assert.deepEqual(rows.map(row=>row.mesh).sort(),meshNames.slice().sort(),`${name} active mesh mapping`);
    assert.ok(rows.every(row=>row.changed>0&&row.maxDelta>1e-8),`${name} active deltas are measurable`);
  }
});

test('morph delta audit documents measurements and visual-validation limits', () => {
  const report=fs.readFileSync(path.join(root,'MORPH-DELTA-AUDIT-VI.txt'),'utf8');
  for(const phrase of ['12/12 tên có ít nhất một delta POSITION khác 0','blink_left','right_eye','0.093408','không chứng minh hình dạng biến dạng đẹp','Chưa xác minh render bằng trình duyệt']) assert.ok(report.includes(phrase),`missing morph audit note: ${phrase}`);
});


test('diagnostics includes accessible combined-expression presets and tracks selected state', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  for(const [key,label] of [['smile-blink','Cười + chớp mắt'],['smile-talk','Cười khi nói'],['round-talk','Môi tròn khi nói']]) {
    assert.match(html,new RegExp(`data-preset=[\"']${key}[\"']`),`missing preset ${key}`);
    assert.ok(html.includes(label),`missing localized label ${label}`);
  }
  assert.match(html,/function clearActivePreset\(\)/);
  assert.match(html,/button\.setAttribute\('aria-pressed','true'\)/);
  assert.match(html,/clearActivePreset\(\);debugWeights=null/);
  assert.match(html,/clearActivePreset\(\);setDebugWeights\(\{\}\)/);
});


test('diagnostic panel can create and apply validated expression JSON snapshots', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  for(const id of ['snapshot-tools','snapshot-create','snapshot-apply','snapshot-json']) assert.match(html,new RegExp(`id=["']${id}["']`),`missing ${id}`);
  assert.match(html,/createSnapshot\(debugWeights\|\|\{\},expectedMorphs,targetUrl\)/);
  assert.match(html,/parseSnapshot\(snapshotJson\.value,expectedMorphs,targetUrl\)/);
  assert.match(html,/Bản ghi thuộc mô hình khác/);
  assert.match(html,/không gửi dữ liệu lên máy chủ/);
});

test('V227 expression baseline manifest is complete, bounded, and explicitly provisional', () => {
  const manifest=JSON.parse(fs.readFileSync(path.join(root,'expression-baseline-cases-v1.json'),'utf8'));
  const expected=['smile','blink_left','blink_right','mouth_open','jaw_open','jaw_hinge','brow_raise','cheek_raise','lip_press','lip_fv','lip_round','tongue_tip'];
  assert.equal(manifest.schema,'ly-lam-lam-expression-baseline-cases');
  assert.equal(manifest.version,1);
  assert.equal(manifest.asset,'./lam-default.glb');
  assert.match(manifest.status,/provisional/);
  assert.deepEqual(manifest.morph_names,expected);
  assert.equal(manifest.cases.length,12);
  assert.equal(new Set(manifest.cases.map(c=>c.id)).size,manifest.cases.length,'case IDs are unique');
  for(const item of manifest.cases){
    assert.equal(typeof item.label_vi,'string');
    assert.equal(typeof item.visual_check,'string');
    assert.deepEqual(Object.keys(item.weights).sort(),expected.slice().sort(),`${item.id} declares every morph`);
    for(const [name,value] of Object.entries(item.weights)) assert.ok(Number.isFinite(value)&&value>=0&&value<=1,`${item.id}.${name} is bounded`);
  }
  const rubric=fs.readFileSync(path.join(root,'EXPRESSION-EVALUATION-VI.txt'),'utf8');
  for(const phrase of ['0 đến 4','chưa được xác nhận trực quan','giữ điều kiện chụp tương đương','Chưa thực hiện kiểm chứng trực quan']) assert.ok(rubric.includes(phrase),`missing evaluation safeguard: ${phrase}`);
});


test('V228 diagnostics integrates the provisional baseline cases with guarded loading and apply action', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  for(const id of ['baseline-tools','baseline-case','baseline-apply','baseline-description']) assert.match(html,new RegExp(`id=["']${id}["']`),`missing ${id}`);
  assert.match(html,/fetch\('\.\/expression-baseline-cases-v1\.json'\)/);
  assert.match(html,/manifest\.schema!==['"]ly-lam-lam-expression-baseline-cases/);
  assert.match(html,/baselineManifest\?\.cases\.find/);
  assert.match(html,/setDebugWeights\(item\.weights\)/);
  assert.match(html,/preset tạm thời/);
});


test('V229 evaluation log is integrated, local-only, and linked to the active case and snapshot', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  for(const id of ['evaluation-tools','evaluation-version','evaluation-device','evaluation-scores','evaluation-observations','evaluation-evidence','evaluation-create','evaluation-json','evaluation-validate','evaluation-result']) assert.match(html,new RegExp(`id=["']${id}["']`),`missing ${id}`);
  assert.match(html,/avatar_expression_evaluation_log\.js/);
  assert.match(html,/evaluationApi\.createRecord/);
  assert.match(html,/snapshot:currentSnapshot\(\)/);
  assert.match(html,/evaluationApi\.parseRecord/);
  assert.match(html,/lastAppliedBaselineCaseId=''/);
  const module=fs.readFileSync(path.join(root,'avatar_expression_evaluation_log.js'),'utf8');
  assert.match(module,/ly-lam-lam-expression-evaluation/);
  assert.match(module,/new Set\(\[0,1,2,3,4,'N\/A'\]\)/);
});


test('V230 evaluation comparison UI and module are integrated', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  for(const id of ['evaluation-compare-tools','evaluation-compare-a','evaluation-compare-b','evaluation-compare-run','evaluation-compare-result']) assert.match(html,new RegExp(`id=["']${id}["']`),`missing ${id}`);
  assert.match(html,/avatar_expression_evaluation_compare\.js/);
  assert.match(html,/AvatarExpressionEvaluationCompare/);
  const module=fs.readFileSync(path.join(root,'avatar_expression_evaluation_compare.js'),'utf8');
  assert.match(module,/case-mismatch/); assert.match(module,/morph-set-mismatch/); assert.match(module,/average_delta/);
});

test('V236 surfaces early startup errors and module rejections to the user', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/window\.addEventListener\('error'/);
  assert.match(html,/window\.addEventListener\('unhandledrejection'/);
  assert.match(html,/Lỗi khởi chạy:/);
  assert.match(html,/Không khởi chạy được:/);
  assert.match(html,/Ứng dụng chưa tải xong mô hình sau 15 giây/);
});

test('V237 startup preflight checks local module paths and core assets without claiming browser success', () => {
  const script=fs.readFileSync(path.join(root,'tools/startup-preflight.cjs'),'utf8');
  assert.match(script,/localSpecifiers/);
  assert.match(script,/lam-default\.glb/);
  assert.match(script,/expression-baseline-cases-v1\.json/);
  assert.match(script,/không kiểm tra được khả năng truy cập mạng/);
  assert.match(script,/không xác minh CDN, WebGL, render, host HTTPS hoặc Safari\/iPhone/);
  const run=require('node:child_process').spawnSync(process.execPath,[path.join(root,'tools/startup-preflight.cjs')],{cwd:root,encoding:'utf8'});
  assert.equal(run.status,0,run.stderr||run.stdout);
  assert.match(run.stdout,/PASS: 14 tệp nguồn, 17 tham chiếu module cục bộ/);
  assert.match(run.stdout+run.stderr,/Bản triển khai mặc định dùng Three\.js tự lưu trữ/);
});

test('V238 static HTTP smoke test serves startup resources with correct status and MIME types', () => {
  const script=fs.readFileSync(path.join(root,'tools/static-http-smoke.cjs'),'utf8');
  assert.match(script,/createServer/);
  assert.match(script,/model\/gltf-binary/);
  assert.match(script,/__startup-smoke_missing__/);
  assert.match(script,/không kiểm tra CDN, WebGL, render hoặc Safari\/iPhone/);
  const run=require('node:child_process').spawnSync(process.execPath,[path.join(root,'tools/static-http-smoke.cjs')],{cwd:root,encoding:'utf8',timeout:15000});
  assert.equal(run.status,0,run.stderr||run.stdout);
  assert.match(run.stdout,/PASS HTTP 200 index\.html/);
  assert.match(run.stdout,/PASS HTTP 200 lam-default\.glb/);
  assert.match(run.stdout,/PASS HTTP 404 cho tài nguyên không tồn tại/);
});



test('V312 classifies WebGL renderer failures before generic local-module failures', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  const errorHandler=html.slice(html.indexOf("window.addEventListener('error', (event) =>"), html.indexOf("window.addEventListener('unhandledrejection', (event) =>"));
  const rejectionStart=html.indexOf("window.addEventListener('unhandledrejection', (event) =>");
  const rejectionHandler=html.slice(rejectionStart, html.indexOf('</script>', rejectionStart));
  assert.ok(errorHandler.indexOf('/webgl|creating.*context|renderer/i.test(message)') < errorHandler.indexOf('window.__lyLamIsLocalStartupFailure(event, message)'), 'WebGL errors must get the specific renderer message first');
  assert.ok(rejectionHandler.indexOf('/webgl|creating.*context|renderer/i.test(message)') < rejectionHandler.indexOf("window.__lyLamIsLocalStartupFailure({ filename: '' }"), 'WebGL rejections must get the specific renderer message first');
  assert.match(html,/Không khởi tạo được đồ họa 3D/);
});

test('V239 gives targeted WebGL startup guidance instead of a generic CDN warning', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/webgl\|creating\.\*context\|renderer/i);
  assert.match(html,/Không khởi tạo được đồ họa 3D/);
  assert.match(html,/Hãy bật WebGL, cập nhật trình duyệt/);
  assert.match(html,/window\.addEventListener\('error'/);
  assert.match(html,/window\.addEventListener\('unhandledrejection'/);
});


test('V240 includes an opt-in CDN connectivity probe with bounded requests and no package mutation', () => {
  const script=fs.readFileSync(path.join(root,'tools/cdn-connectivity-check.cjs'),'utf8');
  assert.match(script,/three@0\.160\.0\/build\/three\.module\.js/);
  assert.match(script,/GLTFLoader\.js/);
  assert.match(script,/OrbitControls\.js/);
  assert.match(script,/https:\/\/unpkg\.com\/three@0\.160\.0\/build\/three\.module\.js/);
  assert.match(script,/req\.on\('timeout'/);
  assert.match(script,/req\.on\('error'/);
  assert.match(script,/chưa xác nhận trình duyệt\/iPhone/);
  assert.match(script,/process\.exitCode = 1/);
});


test('V241 uses bundled Three.js by default and preserves pinned CDN overrides', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/const mode=new URLSearchParams\(location\.search\)\.get\('three'\);const local=mode==='local'\|\|mode===null;/,
    'the omitted query parameter and ?three=local must select local runtime assets');
  assert.match(html,/const base=local\?'\.\/vendor\/three\/':mode==='unpkg'\?'https:\/\/unpkg\.com\/three@0\.160\.0\/':'https:\/\/cdn\.jsdelivr\.net\/npm\/three@0\.160\.0\//,
    'only explicit fallback modes may select the pinned CDN packages');
  assert.match(html,/document\.write\('<script type="importmap">'/);
  for(const asset of ['vendor/three/build/three.module.js','vendor/three/examples/jsm/loaders/GLTFLoader.js','vendor/three/examples/jsm/controls/OrbitControls.js']) {
    const file=path.join(root,asset);
    assert.ok(fs.existsSync(file) && fs.statSync(file).size>1000, 'current runtime asset exists: '+asset);
  }
});

test('Three.js staging tool rejects wrong versions and accepts a minimal official-package fixture', () => {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'lylamlam-vendor-test-'));
  const source=path.join(temp,'three');
  const dest=path.join(root,'vendor','three');
  const prior=fs.existsSync(dest);
  const backup=path.join(temp,'prior-vendor');
  try {
    if(prior) fs.cpSync(dest,backup,{recursive:true});
    fs.mkdirSync(path.join(source,'build'),{recursive:true});
    fs.mkdirSync(path.join(source,'examples/jsm/loaders'),{recursive:true});
    fs.mkdirSync(path.join(source,'examples/jsm/controls'),{recursive:true});
    fs.writeFileSync(path.join(source,'package.json'),JSON.stringify({name:'three',version:'0.160.0'}));
    for(const file of ['build/three.module.js','examples/jsm/loaders/GLTFLoader.js','examples/jsm/controls/OrbitControls.js','LICENSE']) fs.writeFileSync(path.join(source,file),'fixture');
    const script=path.join(root,'tools/vendor-three.cjs');
    fs.writeFileSync(path.join(source,'package.json'),JSON.stringify({name:'three',version:'0.161.0'}));
    const rejected=cp.spawnSync(process.execPath,[script,source],{encoding:'utf8'});
    assert.notEqual(rejected.status,0);
    assert.match(rejected.stderr,/cần gói three@0\.160\.0/);
    fs.writeFileSync(path.join(source,'package.json'),JSON.stringify({name:'three',version:'0.160.0'}));
    const accepted=cp.spawnSync(process.execPath,[script,source],{encoding:'utf8'});
    assert.equal(accepted.status,0,accepted.stderr);
    assert.ok(fs.existsSync(path.join(dest,'build/three.module.js')));
    assert.ok(fs.existsSync(path.join(dest,'examples/jsm/loaders/GLTFLoader.js')));
    assert.ok(fs.existsSync(path.join(dest,'examples/jsm/controls/OrbitControls.js')));
    assert.ok(fs.existsSync(path.join(dest,'LICENSE')));
  } finally {
    fs.rmSync(dest,{recursive:true,force:true});
    if(prior) fs.cpSync(backup,dest,{recursive:true});
    // Preserve the project's vendor tree when this test runs against a packaged build.
    // Only remove the now-empty parent when the test started without a vendor package.
    const vendorRoot=path.join(root,'vendor');
    if(!prior && fs.existsSync(vendorRoot) && fs.readdirSync(vendorRoot).length===0) fs.rmdirSync(vendorRoot);
    fs.rmSync(temp,{recursive:true,force:true});
  }
});


test('V258 Three.js staging validates the import graph before replacing the package', () => {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'lylamlam-v258-vendor-rollback-'));
  const source=path.join(temp,'three');
  const dest=path.join(root,'vendor','three');
  const prior=fs.existsSync(dest);
  const backup=path.join(temp,'prior-vendor');
  try {
    if(prior) fs.cpSync(dest,backup,{recursive:true});
    for(const file of ['build/three.module.js','examples/jsm/loaders/GLTFLoader.js','examples/jsm/controls/OrbitControls.js']) {
      fs.mkdirSync(path.dirname(path.join(source,file)),{recursive:true});
      fs.writeFileSync(path.join(source,file),'export {};');
    }
    fs.writeFileSync(path.join(source,'examples/jsm/loaders/GLTFLoader.js'),'import "../utils/not-present.js";');
    fs.writeFileSync(path.join(source,'LICENSE'),'fixture license');
    fs.writeFileSync(path.join(source,'package.json'),JSON.stringify({name:'three',version:'0.160.0'}));
    const result=cp.spawnSync(process.execPath,[path.join(root,'tools/vendor-three.cjs'),source],{encoding:'utf8'});
    assert.notEqual(result.status,0,'invalid import graph must fail staging');
    assert.match(result.stderr,/không vượt qua kiểm tra import/);
    if(prior) {
      assert.ok(fs.existsSync(path.join(dest,'package.json')),'previous vendor package must be restored');
      assert.equal(fs.readFileSync(path.join(dest,'package.json'),'utf8'),fs.readFileSync(path.join(backup,'package.json'),'utf8'));
    } else assert.equal(fs.existsSync(dest),false,'invalid package must not remain staged');
  } finally {
    fs.rmSync(dest,{recursive:true,force:true});
    if(prior) fs.cpSync(backup,dest,{recursive:true});
    fs.rmSync(path.join(root,'vendor','.three-staging-' + process.pid),{recursive:true,force:true});
    fs.rmSync(path.join(root,'vendor','.three-backup-' + process.pid),{recursive:true,force:true});
    fs.rmSync(temp,{recursive:true,force:true});
    const vendorRoot=path.join(root,'vendor');
    if(fs.existsSync(vendorRoot)&&fs.readdirSync(vendorRoot).length===0) fs.rmdirSync(vendorRoot);
  }
});

test('V242 startup preflight distinguishes absent and incomplete self-hosted Three.js packages', () => {
  const preflight=fs.readFileSync(path.join(root,'tools/startup-preflight.cjs'),'utf8');
  assert.match(preflight,/vendorRequired/);
  assert.match(preflight,/đã tồn tại nhưng thiếu tệp bắt buộc/);
  assert.match(preflight,/Chưa có vendor\/three/);
  assert.match(preflight,/vendorPackage\.version !== '0\.160\.0'/);
  const staging=fs.readFileSync(path.join(root,'tools/vendor-three.cjs'),'utf8');
  assert.match(staging,/three-backup-/);
  assert.match(staging,/if \(hadDestination && fs\.existsSync\(backup\)/);
});


test('V243 provides a pinned npm acquisition path that stages through the existing validator', () => {
  const tool=fs.readFileSync(path.join(root,'tools/fetch-vendor-three.cjs'),'utf8');
  assert.match(tool,/three@0\.160\.0/);
  assert.match(tool,/--ignore-scripts/);
  assert.match(tool,/--package-lock=false/);
  assert.match(tool,/tools',\s*'vendor-three\.cjs/);
  assert.match(tool,/mkdtempSync/);
  assert.match(tool,/rmSync\(temp,\s*\{\s*recursive:\s*true,\s*force:\s*true\s*\}\)/);
  assert.match(tool,/EAI_AGAIN\|ETIMEDOUT\|ECONN/);
});


test('V245 vendor module integrity checker rejects missing relative addon dependencies', () => {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'lylamlam-vendor-edges-'));
  const vendor=path.join(temp,'vendor','three');
  const script=path.join(root,'tools/vendor-module-integrity.cjs');
  try {
    for(const file of ['build/three.module.js','examples/jsm/loaders/GLTFLoader.js','examples/jsm/controls/OrbitControls.js']) {
      fs.mkdirSync(path.dirname(path.join(vendor,file)),{recursive:true});
      fs.writeFileSync(path.join(vendor,file),'export {};');
    }
    fs.writeFileSync(path.join(vendor,'examples/jsm/loaders/GLTFLoader.js'),'import { helper } from "../utils/missing-helper.js"; export { helper };');
    const bad=cp.spawnSync(process.execPath,[script,temp],{encoding:'utf8'});
    assert.notEqual(bad.status,0);
    assert.match(bad.stderr,/thiếu module \.\.\/utils\/missing-helper\.js/);
    fs.mkdirSync(path.join(vendor,'examples/jsm/utils'),{recursive:true});
    fs.writeFileSync(path.join(vendor,'examples/jsm/utils/missing-helper.js'),'export const helper = 1;');
    const good=cp.spawnSync(process.execPath,[script,temp],{encoding:'utf8'});
    assert.equal(good.status,0,good.stderr);
    assert.match(good.stdout,/cạnh import tương đối hợp lệ/);
  } finally { fs.rmSync(temp,{recursive:true,force:true}); }
});


test('V259 Pages preparation rejects broken vendor import graphs without changing index.html', () => {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'lylamlam-pages-bad-graph-'));
  const script=path.join(root,'tools/prepare-pages-deploy.cjs');
  const htmlPath=path.join(temp,'index.html');
  const original=fs.readFileSync(path.join(root,'index.html'),'utf8');
  try {
    fs.writeFileSync(htmlPath,original);
    const vendor=path.join(temp,'vendor','three');
    for(const file of ['build/three.module.js','examples/jsm/loaders/GLTFLoader.js','examples/jsm/controls/OrbitControls.js']) {
      fs.mkdirSync(path.dirname(path.join(vendor,file)),{recursive:true});
      fs.writeFileSync(path.join(vendor,file),'export {};');
    }
    fs.writeFileSync(path.join(vendor,'examples/jsm/loaders/GLTFLoader.js'),'import "../utils/not-installed.js"; export {};');
    fs.writeFileSync(path.join(vendor,'LICENSE'),'fixture license');
    fs.writeFileSync(path.join(vendor,'package.json'),JSON.stringify({name:'three',version:'0.160.0'}));
    const result=cp.spawnSync(process.execPath,[script,temp],{encoding:'utf8'});
    assert.notEqual(result.status,0,'invalid module graph must stop Pages preparation');
    assert.match(result.stderr,/thiếu module/);
    assert.equal(fs.readFileSync(htmlPath,'utf8'),original,'failed preparation must leave index.html unchanged');
  } finally { fs.rmSync(temp,{recursive:true,force:true}); }
});

test('V250 keeps the startup watchdog active until the GLB model loads or a fatal error occurs', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const loaderIndex = html.indexOf('const loader=new GLTFLoader()');
  const bootedIndex = html.indexOf('window.__lyLamAppBooted=true');
  assert.ok(loaderIndex >= 0 && bootedIndex > loaderIndex, 'appBooted must be set only after GLTFLoader success');
  assert.match(html, /if \(!window\.__lyLamAppBooted && !window\.__lyLamBootFailed\)/);
  assert.match(html, /window\.__lyLamRendererReady=true/);
  assert.match(html, /window\.__lyLamBootFailed=true;window\.clearTimeout\(window\.__lyLamBootTimer\);const xhr=e&&e\.target/);
  assert.match(html, /progress=>\{if\(progress\.total>0\)/, 'GLB progress should update the visible loading status');
});

test('V260 tries the npm cache before network access for pinned Three.js acquisition', () => {
  const tool=fs.readFileSync(path.join(root,'tools/fetch-vendor-three.cjs'),'utf8');
  assert.match(tool,/--offline/);
  assert.match(tool,/bộ nhớ đệm npm ngoại tuyến/);
  assert.match(tool,/timeout: 5000/,'offline cache lookup must be bounded');
  assert.match(tool,/timeout: 60000/,'online registry request must not hang indefinitely');
  assert.match(tool,/if \(!offline\.error && offline\.status === 0\)/);
  assert.match(tool,/registry\.npmjs\.org/,'the official npm registry remains the first online source');
  assert.match(tool,/registry\.npmmirror\.com/,'a mirror is attempted only after a network-classified official-registry failure');
  assert.match(tool,/run\(npm, \[\.\.\.installArgs, '--registry', registry\.url, 'three@0\.160\.0'\]\)/,'each online attempt remains pinned to the exact Three.js version');
  assert.match(tool,/three@0\.160\.0/,'both paths must remain pinned to the official version');
});


test('V251 preserves the startup retry button when status text changes and exposes it on failure', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /<span id="status-message">Đang tải avatar…<\/span><button id="retry-startup" type="button" hidden>Thử tải lại<\/button>/);
  assert.match(html, /retry-startup[\s\S]*?addEventListener\('click',\s*\(\) => location\.reload\(\)\)/);
  assert.match(html, /window\.__lyLamShowRetry = \(\) =>/);
  assert.match(html, /(?:status\.firstChild\.textContent|statusMessage\.textContent)=.*window\.__lyLamShowRetry\(\)/);
  assert.match(html, /statusMessage\.textContent=`Đang tải mô hình 3D…/);
  assert.doesNotMatch(html, /status\.textContent=/, 'status updates must not replace and remove the retry button');
});


test('V252 startup timeout includes contextual network, Three.js mode, and WebGL diagnostics', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /window\.__lyLamStartupDiagnostics = \(\) =>/);
  assert.match(html, /navigator\.onLine \? 'đang báo online' : 'đang báo offline'/);
  assert.match(html, /thư viện nội bộ \(three=local\)/);
  assert.match(html, /getContext\('webgl2'\) \|\| canvas\.getContext\('webgl'\)/);
  assert.match(html, /window\.__lyLamStartupDiagnostics\(\)/);
  assert.match(html, /window\.__lyLamShowRetry\(\)/);
});

test('V253 GLB load failure reports asset URL, guarded error detail, and startup context', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /const xhr=e&&e\.target&&typeof e\.target\.status==='number'/);
  assert.match(html, /const kind=httpStatus>=400\?/);
  assert.match(html, /`\$\{kind\}: không tải được \$\{targetUrl\}/);
  assert.match(html, /\$\{window\.__lyLamStartupDiagnostics\(\)\}/);
  assert.match(html, /window\.__lyLamShowRetry\(\);console\.error\('GLTF load failed',e\)/);
});


test('V300 GLB loader errors report HTTP status separately from network and parse failures', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /const xhr=e&&e\.target&&typeof e\.target\.status==='number'\?e\.target:null/);
  assert.match(html, /const httpStatus=xhr&&xhr\.status>0\?xhr\.status:0/);
  assert.match(html, /Máy chủ từ chối hoặc không tìm thấy GLB \(HTTP \$\{httpStatus\}\)/);
  assert.match(html, /Lỗi mạng, CORS hoặc quyền truy cập tài nguyên/);
  assert.match(html, /Lỗi đọc hoặc phân tích GLB/);
  assert.match(html, /phản hồi máy chủ, HTTPS và quyền truy cập/);
});


test('V254 WebGL context loss exposes recovery action and restoration clears it only when avatar is ready', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /webglcontextlost',event=>\{event\.preventDefault\(\);statusMessage\.textContent=.*window\.__lyLamShowRetry\(\);\}\)/);
  assert.match(html, /webglcontextrestored',\(\)=>\{resizeRenderer\(\);statusMessage\.textContent=viewerReady\?/);
  assert.match(html, /if\(viewerReady\)\{const retry=document\.querySelector\('#retry-startup'\), modeButton=document\.querySelector\('#switch-three-mode'\);if\(retry\)retry\.hidden=true;if\(modeButton\)modeButton\.hidden=true;\}/);
});


test('V255 offers a query-preserving switch between CDN and self-hosted Three.js after startup failure', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /id="switch-three-mode" type="button" hidden/);
  assert.match(html, /new URL\(location\.href\)/);
  assert.match(html, /url\.searchParams\.set\('three', next\)/);
  assert.match(html, /Thử thư viện nội bộ \(cần vendor\/three\)/);
  assert.match(html, /Thử CDN jsDelivr/);
  assert.match(html, /if \(threeModeSwitch\).*threeModeSwitch\.hidden = false/s);
});


test('V256/V257 preflight required local assets before switching into local mode', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /threeModeSwitch\?\.addEventListener\('click', async \(\) =>/);
  assert.match(html, /const requiredAssets = \['\.\/vendor\/three\/build\/three\.module\.js'/);
  assert.match(html, /Promise\.all\(requiredAssets\.map\(async asset =>/);
  assert.match(html, /const missing = probes\.filter\(result => !result\.ok\)/);
  assert.match(html, /thiếu hoặc không truy cập được: \$\{detail\}/);
  assert.match(html, /Giữ nguyên chế độ hiện tại/);
  assert.match(html, /url\.searchParams\.set\('three', next\); location\.assign\(url\.href\)/);
});

test('V257 probes local Three.js core, both required addons, and avatar GLB before switching', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /const requiredAssets = \['\.\/vendor\/three\/build\/three\.module\.js', '\.\/vendor\/three\/examples\/jsm\/loaders\/GLTFLoader\.js', '\.\/vendor\/three\/examples\/jsm\/controls\/OrbitControls\.js', '\.\/lam-default\.glb'\]/);
  assert.match(html, /Promise\.all\(requiredAssets\.map\(async asset =>/);
  assert.match(html, /const missing = probes\.filter\(result => !result\.ok\)/);
  assert.match(html, /thiếu hoặc không truy cập được: \$\{detail\}/);
  assert.match(html, /Hãy đóng gói đúng Three\.js 0\.160\.0 và mô hình GLB/);
});

test('V261 supports a user-supplied local Three.js npm tarball without registry access', () => {
  const tool=fs.readFileSync(path.join(root,'tools/fetch-vendor-three.cjs'),'utf8');
  assert.match(tool,/process\.env\.THREE_TARBALL/);
  assert.match(tool,/THREE_TARBALL không phải tệp tồn tại/);
  assert.match(tool,/run\(npm, \[\.\.\.installArgs, tarball\]\)/);
  assert.match(tool,/vendor-three\.cjs/,'local tarballs must pass through the existing staging validator');
  assert.match(fs.readFileSync(path.join(root,'tools/vendor-three.cjs'),'utf8'),/pkg\.version !== '0\.160\.0'/,'staging must still validate the pinned package version');
});


test('V263 verifies a supplied local Three.js tarball against an optional SHA-512 pin before npm runs', () => {
  const tool=fs.readFileSync(path.join(root,'tools/fetch-vendor-three.cjs'),'utf8');
  assert.match(tool,/THREE_TARBALL_SHA512/);
  assert.match(tool,/createHash\('sha512'\)/);
  assert.match(tool,/SHA-512 của THREE_TARBALL không khớp/);
  assert.ok(tool.indexOf('if (!valid) throw') < tool.indexOf('run(npm, [...installArgs, tarball])'), 'integrity check must precede npm extraction');
  assert.match(tool,/actualSri === expected/,'npm-style SHA-512 SRI values are supported');
});


test('V264 rejects a mismatched SHA-512 tarball pin before invoking npm or staging vendor files', () => {
  const temp=fs.mkdtempSync(path.join(root,'.lylamlam-v264-tarball-pin-'));
  const bin=path.join(temp,'bin'); fs.mkdirSync(bin);
  const npm=path.join(bin,process.platform==='win32'?'npm.cmd':'npm');
  const invoked=path.join(temp,'npm-was-invoked');
  const tarball=path.join(temp,'three.tgz');
  const vendorRoot=path.join(root,'vendor');
  const preservedVendor=path.join(temp,'vendor-original');
  const hadVendor=fs.existsSync(vendorRoot);
  if(hadVendor) fs.renameSync(vendorRoot,preservedVendor);
  fs.writeFileSync(tarball,'fixture archive bytes');
  const command=process.platform==='win32'
    ? `@echo invoked>${invoked}\r\nexit /b 1\r\n`
    : `#!/bin/sh\nprintf invoked > '${invoked}'\nexit 1\n`;
  try {
    fs.writeFileSync(npm,command,{mode:0o755});
    const env={...process.env,PATH:`${bin}${path.delimiter}${process.env.PATH}`,THREE_TARBALL:tarball,THREE_TARBALL_SHA512:'0'.repeat(128)};
    const result=cp.spawnSync(process.execPath,[path.join(root,'tools/fetch-vendor-three.cjs')],{encoding:'utf8',env,timeout:15000});
    assert.notEqual(result.status,0,'a wrong pin must reject the tarball');
    assert.match(result.stderr,/SHA-512 của THREE_TARBALL không khớp/);
    assert.equal(fs.existsSync(invoked),false,'npm must not run before the hash pin is accepted');
    assert.equal(fs.existsSync(path.join(root,'vendor','three')),false,'rejected archive must not create vendor/three');
  } finally {
    if(hadVendor && fs.existsSync(preservedVendor)) fs.renameSync(preservedVendor,vendorRoot);
    fs.rmSync(temp,{recursive:true,force:true});
  }
});


test('V265 accepts matching SHA-512 hex and npm SRI pins before invoking npm', () => {
  const crypto=require('node:crypto');
  const temp=fs.mkdtempSync(path.join(root,'.lylamlam-v265-tarball-pin-positive-'));
  const bin=path.join(temp,'bin'); fs.mkdirSync(bin);
  const npm=path.join(bin,process.platform==='win32'?'npm.cmd':'npm');
  const invoked=path.join(temp,'npm-was-invoked');
  const tarball=path.join(temp,'three.tgz');
  const vendorRoot=path.join(root,'vendor');
  const preservedVendor=path.join(temp,'vendor-original');
  const hadVendor=fs.existsSync(vendorRoot);
  if(hadVendor) fs.renameSync(vendorRoot,preservedVendor);
  fs.writeFileSync(tarball,'fixture archive bytes accepted only for pin-gate test');
  const command=process.platform==='win32'
    ? `@echo invoked>${invoked}\r\nexit /b 23\r\n`
    : `#!/bin/sh\nprintf invoked > '${invoked}'\nexit 23\n`;
  const digest=crypto.createHash('sha512').update(fs.readFileSync(tarball)).digest();
  const pins=[digest.toString('hex'),`sha512-${digest.toString('base64')}`];
  try {
    fs.writeFileSync(npm,command,{mode:0o755});
    for(const pin of pins) {
      fs.rmSync(invoked,{force:true});
      const env={...process.env,PATH:`${bin}${path.delimiter}${process.env.PATH}`,THREE_TARBALL:tarball,THREE_TARBALL_SHA512:pin};
      const result=cp.spawnSync(process.execPath,[path.join(root,'tools/fetch-vendor-three.cjs')],{encoding:'utf8',env,timeout:15000});
      assert.notEqual(result.status,0,'fake npm intentionally fails after integrity validation');
      assert.match(result.stdout,/PASS: SHA-512 tarball khớp giá trị THREE_TARBALL_SHA512/);
      assert.equal(fs.existsSync(invoked),true,'a matching pin should allow npm to be invoked');
      assert.equal(fs.existsSync(path.join(root,'vendor','three')),false,'the fixture must never be staged as a real vendor package');
    }
  } finally {
    if(hadVendor && fs.existsSync(preservedVendor)) fs.renameSync(preservedVendor,vendorRoot);
    fs.rmSync(temp,{recursive:true,force:true});
  }
});


test('V266 can require a SHA-512 pin and rejects an unpinned local tarball before npm runs', () => {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'lylamlam-v266-require-pin-'));
  const bin=path.join(temp,'bin'); fs.mkdirSync(bin);
  const npm=path.join(bin,process.platform==='win32'?'npm.cmd':'npm');
  const invoked=path.join(temp,'npm-was-invoked');
  const tarball=path.join(temp,'three.tgz'); fs.writeFileSync(tarball,'fixture bytes only');
  const command=process.platform==='win32' ? `@echo invoked>${invoked}\r\nexit /b 1\r\n` : `#!/bin/sh\nprintf invoked > '${invoked}'\nexit 1\n`;
  try {
    fs.writeFileSync(npm,command,{mode:0o755});
    const env={...process.env,PATH:`${bin}${path.delimiter}${process.env.PATH}`,THREE_TARBALL:tarball,THREE_TARBALL_SHA512:'',THREE_TARBALL_REQUIRE_SHA512:'1'};
    const result=cp.spawnSync(process.execPath,[path.join(root,'tools/fetch-vendor-three.cjs')],{encoding:'utf8',env,timeout:15000});
    assert.notEqual(result.status,0);
    assert.match(result.stderr,/THREE_TARBALL_REQUIRE_SHA512 đang bật nhưng chưa cung cấp/);
    assert.equal(fs.existsSync(invoked),false,'npm must not run for an unpinned tarball when pin enforcement is enabled');
  } finally { fs.rmSync(temp,{recursive:true,force:true}); }
});


test('V273 retries transient npm registry failures with bounded acquisition timeouts', () => {
  const tool=fs.readFileSync(path.join(root,'tools/fetch-vendor-three.cjs'),'utf8');
  assert.match(tool,/--fetch-retries=2/);
  assert.match(tool,/--fetch-retry-mintimeout=1000/);
  assert.match(tool,/--fetch-retry-maxtimeout=5000/);
  assert.match(tool,/--fetch-timeout=15000/);
  assert.match(tool,/timeout:\s*60000/);
  assert.match(tool,/timeout:\s*5000/);
  assert.match(tool,/ETIMEDOUT/);
});


test('V268 rejects unbound bare package imports in a synthetic staged Three.js tree', () => {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'lylamlam-v268-bare-import-'));
  const vendor=path.join(temp,'vendor','three');
  const build=path.join(vendor,'build');
  const loader=path.join(vendor,'examples','jsm','loaders');
  const controls=path.join(vendor,'examples','jsm','controls');
  try {
    for (const dir of [build,loader,controls]) fs.mkdirSync(dir,{recursive:true});
    fs.writeFileSync(path.join(build,'three.module.js'),'export const ok = true;');
    fs.writeFileSync(path.join(loader,'GLTFLoader.js'),"import * as THREE from 'three';\nimport './helper.js';\nexport class GLTFLoader {}");
    fs.writeFileSync(path.join(loader,'helper.js'),'export const helper = true;');
    fs.writeFileSync(path.join(controls,'OrbitControls.js'),"import * as THREE from 'three'; export class OrbitControls {}");
    let result=cp.spawnSync(process.execPath,[path.join(root,'tools','vendor-module-integrity.cjs'),temp],{encoding:'utf8'});
    assert.equal(result.status,0,result.stderr);
    fs.writeFileSync(path.join(loader,'GLTFLoader.js'),"import * as THREE from 'three';\nimport thing from 'missing-runtime-package';\nexport class GLTFLoader {}");
    result=cp.spawnSync(process.execPath,[path.join(root,'tools','vendor-module-integrity.cjs'),temp],{encoding:'utf8'});
    assert.notEqual(result.status,0);
    assert.match(result.stderr,/import de package không được ánh xạ.*missing-runtime-package/);
  } finally { fs.rmSync(temp,{recursive:true,force:true}); }
});


test('V269 static HTTP smoke checks HEAD metadata and blocks path traversal', () => {
  const result = cp.spawnSync(process.execPath, [path.join(root, 'tools', 'static-http-smoke.cjs')], { encoding: 'utf8', timeout: 15000 });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  assert.match(result.stdout, /PASS HTTP HEAD index\.html/);
  assert.match(result.stdout, /PASS HTTP HEAD lam-default\.glb/);
  assert.match(result.stdout, /PASS HTTP 403 cho đường dẫn thoát khỏi thư mục gốc/);
});



test('V282 local preview server has safe defaults and explicit LAN opt-in', () => {
  const script = fs.readFileSync(path.join(root, 'tools/serve-preview.cjs'), 'utf8');
  assert.match(script, /let host = '127\.0\.0\.1'/);
  assert.match(script, /--host 127\.0\.0\.1\|0\.0\.0\.0/);
  assert.match(script, /fs\.realpathSync\(candidate\)/, 'must prevent symlink escapes');
  assert.match(script, /req\.method !== 'GET' && req\.method !== 'HEAD'/);
  assert.match(script, /model\/gltf-binary/);
  assert.match(script, /--three cdn\|unpkg\|local/);
  assert.match(script, /threeMode === 'local' \? '\?three=local' : threeMode === 'unpkg' \? '\?three=unpkg' : ''/);
  assert.match(script, /iPhone cùng Wi-Fi:.*\$\{suffix\}/);
  assert.match(script, /x-content-type-options/);
  const result = cp.spawnSync(process.execPath, [path.join(root, 'tools/serve-preview.cjs'), '--help'], { encoding: 'utf8', timeout: 5000 });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /localhost/);
  assert.match(result.stdout, /mạng tin cậy/);
});


test('V284 preview server prints the URL matching the selected Three.js import-map mode', async () => {
  const child = cp.spawn(process.execPath, [path.join(root, 'tools/serve-preview.cjs'), '--host', '127.0.0.1', '--port', '0', '--root', root, '--three', 'local'], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
  let output = '';
  try {
    const line = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error(`server did not print URL; output=${output}`)), 3000);
      child.stdout.on('data', chunk => {
        output += chunk.toString();
        const match = output.match(/URL: (http:\/\/127\.0\.0\.1:\d+\/\?three=local)/);
        if (match) { clearTimeout(timeout); resolve(match[1]); }
      });
      child.once('error', error => { clearTimeout(timeout); reject(error); });
      child.once('exit', code => { clearTimeout(timeout); reject(new Error(`server exited early (${code}); output=${output}`)); });
    });
    assert.match(line, /\?three=local$/);
    assert.match(output, /Chế độ|URL:/);
  } finally {
    child.kill('SIGTERM');
  }
});

test('V285 alternate unpkg mode prints a matching query URL and stays version-pinned', async () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /https:\/\/unpkg\.com\/three@0\.160\.0\//);
  const child = cp.spawn(process.execPath, [path.join(root, 'tools/serve-preview.cjs'), '--host', '127.0.0.1', '--port', '0', '--root', root, '--three', 'unpkg'], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
  let output = '';
  try {
    const line = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error(`unpkg server did not print URL; output=${output}`)), 3000);
      child.stdout.on('data', chunk => {
        output += chunk.toString();
        const match = output.match(/URL: (http:\/\/127\.0\.0\.1:\d+\/\?three=unpkg)/);
        if (match) { clearTimeout(timeout); resolve(match[1]); }
      });
      child.once('error', error => { clearTimeout(timeout); reject(error); });
      child.once('exit', code => { clearTimeout(timeout); reject(new Error(`server exited early (${code}); output=${output}`)); });
    });
    assert.match(line, /\?three=unpkg$/);
    assert.match(output, /CDN|URL:/);
  } finally {
    child.kill('SIGTERM');
  }
});

test('V283 one-command preview launcher selects local Three.js only when all required assets exist', () => {
  const script = fs.readFileSync(path.join(root, 'tools/start-preview.cjs'), 'utf8');
  assert.match(script, /vendor\/three\/build\/three\.module\.js/);
  assert.match(script, /vendor\/three\/examples\/jsm\/loaders\/GLTFLoader\.js/);
  assert.match(script, /vendor\/three\/examples\/jsm\/controls\/OrbitControls\.js/);
  assert.match(script, /CDN jsDelivr/);
  assert.match(script, /'--three', threeMode/);
  assert.match(script, /'unpkg'/);
  assert.match(script, /CDN thay thế unpkg/);
  assert.match(script, /--local-three/);
  assert.match(script, /--lan/);
  const result = cp.spawnSync(process.execPath, [path.join(root, 'tools/start-preview.cjs'), '--help'], { encoding: 'utf8', timeout: 5000 });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /node tools\/start-preview\.cjs/);
  assert.match(result.stdout, /mạng tin cậy/);
  const vendorRoot = path.join(root, 'vendor');
  const hiddenVendor = path.join(root, `.vendor-test-hidden-${process.pid}`);
  const hadVendor = fs.existsSync(vendorRoot);
  try {
    if (hadVendor) fs.renameSync(vendorRoot, hiddenVendor);
    const missingLocal = cp.spawnSync(process.execPath, [path.join(root, 'tools/start-preview.cjs'), '--local-three'], { encoding: 'utf8', timeout: 5000 });
    assert.notEqual(missingLocal.status, 0, 'local mode must fail closed when the vendor bundle is missing');
    assert.match(missingLocal.stderr, /Không thể khởi chạy với Three\.js nội bộ/);
  } finally {
    if (hadVendor && fs.existsSync(hiddenVendor)) fs.renameSync(hiddenVendor, vendorRoot);
  }
});

test('V293 local preview launcher validates the complete vendor module graph before serving', async () => {
  const script = fs.readFileSync(path.join(root, 'tools/start-preview.cjs'), 'utf8');
  assert.match(script, /vendor-module-integrity\.cjs/);
  assert.match(script, /if \(useLocal\)/);
  assert.match(script, /đồ thị module thất bại/);
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'lylamlam-v293-launcher-'));
  const write = (relative, content='// valid fixture\n') => {
    const file = path.join(temp, relative);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, content);
  };
  write('lam-default.glb', 'fixture');
  write('vendor/three/build/three.module.js');
  write('vendor/three/examples/jsm/loaders/GLTFLoader.js', "import { Group } from 'three';\n");
  write('vendor/three/examples/jsm/controls/OrbitControls.js', "import { EventDispatcher } from 'three';\n");
  const launcher = path.join(root, 'tools/start-preview.cjs');
  let child;
  try {
    child = cp.spawn(process.execPath, [launcher, '--local-three', '--root', temp, '--port', '0'], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    const url = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error(`local preview did not print URL; output=${output}`)), 4000);
      child.stdout.on('data', chunk => {
        output += chunk.toString();
        const match = output.match(/URL: (http:\/\/127\.0\.0\.1:\d+\/\?three=local)/);
        if (match) { clearTimeout(timeout); resolve(match[1]); }
      });
      child.stderr.on('data', chunk => { output += chunk.toString(); });
      child.once('error', error => { clearTimeout(timeout); reject(error); });
      child.once('exit', code => { clearTimeout(timeout); reject(new Error(`launcher exited early (${code}); output=${output}`)); });
    });
    assert.match(url, /\?three=local$/);
    assert.match(output, /mô-đun Three\.js đã quét/);
  } finally {
    if (child && child.exitCode === null) {
      child.kill('SIGTERM');
      await new Promise(resolve => {
        const timeout = setTimeout(resolve, 1500);
        child.once('exit', () => { clearTimeout(timeout); resolve(); });
      });
    }
  }
  // A missing relative import must stop the launcher before it starts serving.
  write('vendor/three/examples/jsm/loaders/GLTFLoader.js', "import '../missing-module.js';\n");
  const broken = cp.spawnSync(process.execPath, [launcher, '--local-three', '--root', temp, '--port', '0'], { cwd: root, encoding: 'utf8', timeout: 5000 });
  assert.notEqual(broken.status, 0);
  assert.match(broken.stderr, /đồ thị module thất bại/);
  assert.match(broken.stderr, /thiếu module/);
  fs.rmSync(temp, { recursive: true, force: true });
});

test('V288 retries the pinned Three.js acquisition through the npm mirror after a network-only failure', () => {
  const tool = fs.readFileSync(path.join(root, 'tools/fetch-vendor-three.cjs'), 'utf8');
  assert.match(tool, /registry\.npmjs\.org/);
  assert.match(tool, /registry\.npmmirror\.com/);
  assert.match(tool, /if \(!networkFailure\) throw error/,
    'non-network install errors must not be hidden by a registry switch');
  assert.match(tool, /three@0\.160\.0/);
  assert.match(tool, /--ignore-scripts/);
});

test('V287 startup watchdog tries the guarded alternate CDN when module loading stalls', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const timerStart = html.indexOf('window.__lyLamBootTimer = window.setTimeout');
  const timerEnd = html.indexOf('window.addEventListener(', timerStart + 10);
  assert.notEqual(timerStart, -1, 'startup watchdog exists');
  assert.ok(timerEnd > timerStart, 'watchdog ends before global error handler');
  const watchdog = html.slice(timerStart, timerEnd);
  assert.match(watchdog, /if \(window\.__lyLamTryAutomaticUnpkgFallback\(\)\) return;/,
    'a stalled module request should trigger one guarded alternate-CDN attempt before showing the timeout message');
  assert.match(watchdog, /15000\)/, 'watchdog keeps the documented 15-second timeout');
});

test('V286 retries the alternate pinned CDN once after an early module startup failure', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /window\.__lyLamTryAutomaticUnpkgFallback\s*=\s*\(\)\s*=>/);
  assert.match(html, /ly-lam-lam-three-unpkg-fallback:/);
  assert.match(html, /sessionStorage\.getItem\(key\) === '1'/);
  assert.match(html, /params\.set\('three', 'unpkg'\)/);
  assert.match(html, /if \(window\.__lyLamTryAutomaticUnpkgFallback\(\)\) return;/);
  assert.match(html, /A stalled module fetch may not raise a useful window error/);
  assert.match(html, /const selectedMode = new URLSearchParams\(location\.search\)\.get\('three'\)/);
  assert.match(html, /selectedMode === 'unpkg' \? 'CDN unpkg \(three=unpkg\)'/);
  assert.match(html, /if \(window\.__lyLamRendererReady\) return false/);
  assert.match(html, /sessionStorage\.removeItem\(`ly-lam-lam-three-unpkg-fallback:/);
});

test('V292 CDN fallback remains available when sessionStorage is blocked and uses URL loop guard', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const start = html.indexOf('window.__lyLamTryAutomaticUnpkgFallback = () => {');
  const end = html.indexOf('window.__lyLamBootTimer =', start);
  assert.ok(start >= 0 && end > start, 'fallback helper is present before startup watchdog');
  const helper = html.slice(start, end).replace(/^window\.__lyLamTryAutomaticUnpkgFallback = /, 'globalThis.tryFallback = ');
  const vm = require('node:vm');
  const replaced = [];
  const context = {
    URLSearchParams,
    location: { search: '?diagnostics=1', pathname: '/index.html', hash: '#avatar', replace: value => replaced.push(value) },
    window: { __lyLamRendererReady: false },
    sessionStorage: { getItem() { throw new Error('storage blocked'); }, setItem() { throw new Error('storage blocked'); } }
  };
  vm.runInNewContext(helper, context);
  assert.equal(context.tryFallback(), true, 'blocked storage should not prevent a first fallback');
  assert.equal(replaced.length, 1);
  const target = new URL(replaced[0], 'https://example.test');
  assert.equal(target.searchParams.get('three'), 'unpkg');
  assert.equal(target.searchParams.get('threeFallbackAttempted'), '1');
  assert.equal(target.searchParams.get('diagnostics'), '1', 'other query parameters are preserved');
  assert.equal(target.hash, '#avatar', 'URL fragment is preserved');
  context.location.search = target.search;
  assert.equal(context.tryFallback(), false, 'URL marker prevents a loop when storage is unavailable');
  assert.equal(replaced.length, 1);
  assert.match(html, /cleanUrl\.searchParams\.delete\('threeFallbackAttempted'\)/, 'successful boot cleans up the transient URL marker');
});

test('V289 exports a portable Three.js tarball only when it matches npm dist.integrity', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'lylamlam-v289-export-test-'));
  const bin = path.join(temp, 'bin');
  const out = path.join(temp, 'bundle');
  fs.mkdirSync(bin, { recursive: true });
  const fixtureTarball = path.join(temp, 'three-0.160.0.tgz');
  const fixtureBytes = Buffer.from('test tarball fixture for integrity validation\n');
  fs.writeFileSync(fixtureTarball, fixtureBytes);
  const crypto = require('node:crypto');
  const actualIntegrity = `sha512-${crypto.createHash('sha512').update(fixtureBytes).digest('base64')}`;
  const fakeNpm = path.join(bin, 'npm');
  fs.writeFileSync(fakeNpm, `#!/usr/bin/env node\nconst fs=require('node:fs');const path=require('node:path');const a=process.argv.slice(2);if(a[0]==='view'){process.stdout.write(JSON.stringify(process.env.FAKE_VIEW_INTEGRITY||'${actualIntegrity}'));process.exit(0)}if(a[0]==='pack'){const d=a[a.indexOf('--pack-destination')+1];const f='three-0.160.0.tgz';fs.copyFileSync(process.env.FIXTURE_TARBALL,path.join(d,f));process.stdout.write(JSON.stringify([{filename:f,integrity:'${actualIntegrity}'}]));process.exit(0)}process.exit(2);\n`);
  fs.chmodSync(fakeNpm, 0o755);
  if (process.platform === 'win32') {
    // Windows runners cannot execute the POSIX-style fake npm fixture directly.
    // Keep its JavaScript logic identical and expose it through a small npm.cmd shim.
    fs.copyFileSync(fakeNpm, path.join(bin, 'fake-npm.cjs'));
    fs.writeFileSync(path.join(bin, 'npm.cmd'), '@echo off\r\nnode "%~dp0fake-npm.cjs" %*\r\nexit /b %ERRORLEVEL%\r\n');
  }
  const script = path.join(root, 'tools/export-three-offline-bundle.cjs');
  const env = { ...process.env, PATH: `${bin}${path.delimiter}${process.env.PATH}`, FIXTURE_TARBALL: fixtureTarball };
  try {
    let result = cp.spawnSync(process.execPath, [script, '--out', out], { encoding: 'utf8', env, timeout: 10000 });
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    assert.deepEqual(fs.readFileSync(path.join(out, 'three-0.160.0.tgz')), fixtureBytes);
    const manifest = fs.readFileSync(path.join(out, 'THREE-OFFLINE-MANIFEST.txt'), 'utf8');
    assert.match(manifest, new RegExp(actualIntegrity.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    assert.match(manifest, /THREE_TARBALL_REQUIRE_SHA512=1/);

    // Re-running export into the same directory should refresh the verified bundle
    // rather than failing on COPYFILE_EXCL after a previous successful run.
    result = cp.spawnSync(process.execPath, [script, '--out', out], { encoding: 'utf8', env, timeout: 10000 });
    assert.equal(result.status, 0, `repeat export failed: ${result.stdout}\n${result.stderr}`);
    assert.deepEqual(fs.readFileSync(path.join(out, 'three-0.160.0.tgz')), fixtureBytes);
    assert.match(fs.readFileSync(path.join(out, 'THREE-OFFLINE-MANIFEST.txt'), 'utf8'), /Package: three@0\.160\.0/);

    const mismatchOut = path.join(temp, 'mismatch-bundle');
    result = cp.spawnSync(process.execPath, [script, '--out', mismatchOut], {
      encoding: 'utf8', env: { ...env, FAKE_VIEW_INTEGRITY: 'sha512-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==' }, timeout: 10000
    });
    assert.notEqual(result.status, 0, 'must refuse a tarball whose bytes differ from registry integrity metadata');
    assert.match(result.stderr, /Integrity tarball không khớp metadata npm/);
    assert.equal(fs.existsSync(path.join(mismatchOut, 'three-0.160.0.tgz')), false);
  } finally { fs.rmSync(temp, { recursive: true, force: true }); }
});


test('V291 offline bundle exporter falls back to mirror only for network errors and pins metadata to same registry', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'lylamlam-v291-export-fallback-test-'));
  const bin = path.join(temp, 'bin');
  const out = path.join(temp, 'bundle');
  fs.mkdirSync(bin, { recursive: true });
  const fixtureTarball = path.join(temp, 'three-0.160.0.tgz');
  const fixtureBytes = Buffer.from('v291 registry mirror fixture\n');
  fs.writeFileSync(fixtureTarball, fixtureBytes);
  const crypto = require('node:crypto');
  const integrity = `sha512-${crypto.createHash('sha512').update(fixtureBytes).digest('base64')}`;
  const fakeNpm = path.join(bin, 'npm');
  fs.writeFileSync(fakeNpm, `#!/usr/bin/env node
const fs=require('node:fs');const path=require('node:path');const a=process.argv.slice(2);const r=a[a.indexOf('--registry')+1]||'';fs.appendFileSync(process.env.FAKE_LOG,JSON.stringify({cmd:a[0],registry:r})+'\\n');if(r==='https://registry.npmjs.org/') {process.stderr.write('getaddrinfo EAI_AGAIN registry.npmjs.org');process.exit(1)}if(r!=='https://registry.npmmirror.com/')process.exit(3);if(a[0]==='view'){process.stdout.write(JSON.stringify('${integrity}'));process.exit(0)}if(a[0]==='pack'){const d=a[a.indexOf('--pack-destination')+1];const f='three-0.160.0.tgz';fs.copyFileSync(process.env.FIXTURE_TARBALL,path.join(d,f));process.stdout.write(JSON.stringify([{filename:f,integrity:'${integrity}'}]));process.exit(0)}process.exit(2);
`);
  fs.chmodSync(fakeNpm, 0o755);
  if (process.platform === 'win32') {
    // Windows runners cannot execute the POSIX-style fake npm fixture directly.
    // Keep its JavaScript logic identical and expose it through a small npm.cmd shim.
    fs.copyFileSync(fakeNpm, path.join(bin, 'fake-npm.cjs'));
    fs.writeFileSync(path.join(bin, 'npm.cmd'), '@echo off\r\nnode "%~dp0fake-npm.cjs" %*\r\nexit /b %ERRORLEVEL%\r\n');
  }
  const log = path.join(temp, 'npm-log.jsonl');
  try {
    const result = cp.spawnSync(process.execPath, [path.join(root, 'tools/export-three-offline-bundle.cjs'), '--out', out], {
      encoding: 'utf8', timeout: 10000,
      env: { ...process.env, PATH: `${bin}${path.delimiter}${process.env.PATH}`, FIXTURE_TARBALL: fixtureTarball, FAKE_LOG: log }
    });
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    assert.match(result.stdout, /mirror npm npmmirror/);
    const calls = fs.readFileSync(log, 'utf8').trim().split('\n').map(line => JSON.parse(line));
    assert.deepEqual(calls.map(c => [c.cmd, c.registry]), [
      ['view', 'https://registry.npmjs.org/'],
      ['view', 'https://registry.npmmirror.com/'],
      ['pack', 'https://registry.npmmirror.com/']
    ]);
    const manifest = fs.readFileSync(path.join(out, 'THREE-OFFLINE-MANIFEST.txt'), 'utf8');
    assert.match(manifest, /registry\.npmmirror\.com/);
    assert.deepEqual(fs.readFileSync(path.join(out, 'three-0.160.0.tgz')), fixtureBytes);
  } finally { fs.rmSync(temp, { recursive: true, force: true }); }
});

test('V290 offline bundle importer verifies both manifest hashes before invoking staging', () => {
  const importer = fs.readFileSync(path.join(root, 'tools/import-three-offline-bundle.cjs'), 'utf8');
  assert.match(importer, /THREE-OFFLINE-MANIFEST\.txt/);
  assert.match(importer, /SHA-512 SRI/);
  assert.match(importer, /SHA-512 hex/);
  assert.match(importer, /actualHex\.toLowerCase\(\) !== hex\.toLowerCase\(\) \|\| actualSri !== sri/);
  assert.match(importer, /THREE_TARBALL_REQUIRE_SHA512: '1'/);
  assert.match(importer, /spawnSync\(process\.execPath, \[fetcher\]/);
  assert.match(importer, /Không giải nén gói/);
});

test('V290 offline bundle importer rejects a changed tarball before calling the staging tool', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'lylamlam-v290-import-test-'));
  const bundle = path.join(temp, 'bundle');
  fs.mkdirSync(bundle);
  const bytes = Buffer.from('untrusted changed archive');
  fs.writeFileSync(path.join(bundle, 'three-0.160.0.tgz'), bytes);
  const crypto = require('node:crypto');
  const wrong = Buffer.alloc(64, 7);
  const sri = `sha512-${wrong.toString('base64')}`;
  const hex = wrong.toString('hex');
  fs.writeFileSync(path.join(bundle, 'THREE-OFFLINE-MANIFEST.txt'), [
    'Package: three@0.160.0', `SHA-512 SRI: ${sri}`, `SHA-512 hex: ${hex}`,
    'Tarball: three-0.160.0.tgz', ''
  ].join('\n'));
  try {
    const result = cp.spawnSync(process.execPath, [path.join(root, 'tools/import-three-offline-bundle.cjs'), '--bundle-dir', bundle], {
      encoding: 'utf8', timeout: 10000
    });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /SHA-512 tarball không khớp manifest/);
    assert.doesNotMatch(result.stdout, /Đang cài gói Three\.js/);
  } finally { fs.rmSync(temp, { recursive: true, force: true }); }
});


test('V296 distinguishes a stalled GLB request from a stalled Three.js module fetch', () => {
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/if\s*\(window\.__lyLamRendererReady\)\s*\{\s*window\.__lyLamBootFailed\s*=\s*true;/);
  assert.match(html,/Mô hình GLB chưa tải xong sau 15 giây/);
  assert.match(html,/A stalled module fetch may not raise a useful window error/);
  assert.match(html,/window\.__lyLamAppBooted=true; window\.__lyLamBootFailed=false; window\.clearTimeout\(window\.__lyLamBootTimer\)/);
  assert.match(html,/if\(retryButton\)retryButton\.hidden=true; if\(modeButton\)modeButton\.hidden=true/);
});


test('V306 startup gate exercises the actual preview server and bundled Three.js assets', () => {
  const script=fs.readFileSync(path.join(root,'tools/preview-server-integration.cjs'),'utf8');
  assert.match(script,/serve-preview\.cjs/);
  assert.match(script,/vendor\/three\/build\/three\.module\.js/);
  assert.match(script,/lam-default\.glb/);
  assert.match(script,/path traversal should be HTTP 403/);
  const gate=fs.readFileSync(path.join(root,'tools/verify-startup.cjs'),'utf8');
  assert.match(gate,/preview-server-integration\.cjs/);
});


test('V307 Windows launcher requests browser auto-open only after the preview server prints its ready URL', () => {
  const launcher = fs.readFileSync(path.join(root, 'tools/start-preview.cjs'), 'utf8');
  const bat = fs.readFileSync(path.join(root, 'START-LAM-LAM-WINDOWS.bat'), 'utf8');
  assert.match(launcher, /--open-browser/);
  assert.match(launcher, /URL: \(http:/);
  assert.match(launcher, /process\.platform === 'win32'/);
  assert.match(launcher, /start', '', url/);
  assert.match(launcher, /hãy mở URL ở dòng trên/);
  assert.match(bat, /start-preview\.cjs --local-three --open-browser/);
});


test('V308 exposes a copyable browser startup report for WebGL and asset failures', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /id="startup-report-button"/);
  assert.match(html, /id="startup-report-text"/);
  assert.match(html, /async function collectStartupReport\(\)/);
  assert.match(html, /WEBGL_lose_context/);
  assert.match(html, /vendor\/three\/build\/three\.module\.js/);
  assert.match(html, /navigator\.clipboard\.writeText\(startupReportText\.value\)/);
  assert.match(html, /window\.__lyLamShowRetry = \(\) =>[\s\S]*startupReportButton\.hidden = false/);
});


test('V311 startup report identifies bundled Three.js as the true default and distinguishes explicit CDN modes', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.ok(html.includes("'thư viện nội bộ (mặc định/local)'"));
  assert.ok(html.includes("mode === 'unpkg' ? 'CDN unpkg' : mode === 'cdn' ? 'CDN jsDelivr'"));
  assert.ok(html.includes("`tham số không hợp lệ (${mode})`"));
  assert.doesNotMatch(html, /Three\.js mode:.*cdn mặc định/);
});
