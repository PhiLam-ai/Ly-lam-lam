# Archived legacy package-integrity tests (preserved, not auto-run)

These 16 tests asserted behavior of a retired GitHub Pages build pipeline: `.github/workflows/deploy.yml`, staging npm/Three.js from inside the deployed directory, `dist` artifact assembly, or a `.nojekyll`/module manifest no longer required by the current `v312-work` payload. The active deploy workflow is repository-root `.github/workflows/main.yml` and uploads `./v312-work` directly. Their assertions are preserved below for historical evidence, but intentionally removed from the active `v312-work/tests/package-integrity.test.cjs` run because they fail against the wrong target and do not exercise the current deployment path.

This is not a blanket claim that all underlying ideas are useless: current deployment protection is tested in `automation/tests/v312-package-integrity.test.cjs`, including that actual deploy workflow uses `main.yml`, gates deploy on tests, ships runtime files and has no reliance on the retired builder. Any revived artifact builder must add new tests for that builder rather than reusing these wrong-root tests unchanged.

Original blocks removed from the active diagnostic file: **16**. Their test names are retained exactly.

## deploy package contains required root files and workflow

```javascript
test('deploy package contains required root files and workflow', () => {
  for (const file of ['index.html','lam-default.glb','module.mjs','tools/export-three-offline-bundle.cjs','tools/import-three-offline-bundle.cjs','avatar_expression_snapshot.js','avatar_expression_compare.js','avatar_expression_evaluation_log.js','avatar_expression_evaluation_compare.js','avatar_expression_evaluation_report.js','avatar_expression_evaluation_aggregate.js','avatar_expression_evidence_audit.js','expression-baseline-cases-v1.json','EXPRESSION-EVALUATION-VI.txt','README-VI.txt','VERSION.txt','.nojekyll','.github/workflows/deploy.yml']) {
    assert.ok(fs.existsSync(path.join(root,file)), `missing ${file}`);
  }
});
```

## GitHub Pages workflow gates deployment on passing regression tests

```javascript
test('GitHub Pages workflow gates deployment on passing regression tests', () => {
  const workflow=fs.readFileSync(path.join(root,'.github/workflows/deploy.yml'),'utf8');
  const testStep=workflow.indexOf('node --test tests/*.test.cjs');
  const deployStep=workflow.indexOf('uses: actions/deploy-pages@v4');
  assert.ok(testStep>=0,'regression tests are wired into workflow');
  assert.ok(deployStep>testStep,'deployment comes after tests');
});
```

## V244 GitHub Pages deployment stages pinned Three.js and defaults to self-hosted imports

```javascript
test('V244 GitHub Pages deployment stages pinned Three.js and defaults to self-hosted imports', () => {
  const workflow=fs.readFileSync(path.join(root,'.github/workflows/deploy.yml'),'utf8');
  assert.match(workflow,/node tools\/fetch-vendor-three\.cjs/);
  assert.match(workflow,/node tools\/prepare-pages-deploy\.cjs/);
  assert.match(workflow,/node tools\/startup-preflight\.cjs/);
  assert.match(workflow,/node tools\/static-http-smoke\.cjs/);
  const prepare=fs.readFileSync(path.join(root,'tools/prepare-pages-deploy.cjs'),'utf8');
  assert.match(prepare,/pkg\.version !== '0\.160\.0'/);
  assert.match(prepare,/get\('three'\)!=='cdn'/);
  assert.match(prepare,/vendor\/three/);
  const preflight=fs.readFileSync(path.join(root,'tools/startup-preflight.cjs'),'utf8');
  assert.match(preflight,/mode===null/);
});
```

## V244 deployment preparation fails closed without a complete pinned local vendor

```javascript
test('V244 deployment preparation fails closed without a complete pinned local vendor', () => {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'lylamlam-pages-test-'));
  const script=path.join(root,'tools/prepare-pages-deploy.cjs');
  try {
    fs.writeFileSync(path.join(temp,'index.html'),fs.readFileSync(path.join(root,'index.html'),'utf8'));
    const missing=cp.spawnSync(process.execPath,[script,temp],{encoding:'utf8'});
    assert.notEqual(missing.status,0);
    assert.match(missing.stderr,/thiếu vendor\/three/);
    const vendor=path.join(temp,'vendor','three');
    for(const file of ['build/three.module.js','examples/jsm/loaders/GLTFLoader.js','examples/jsm/controls/OrbitControls.js']) {
      fs.mkdirSync(path.dirname(path.join(vendor,file)),{recursive:true});
      fs.writeFileSync(path.join(vendor,file),'fixture');
    }
    fs.writeFileSync(path.join(vendor,'LICENSE'),'fixture license');
    fs.writeFileSync(path.join(vendor,'package.json'),JSON.stringify({name:'three',version:'0.160.0'}));
    const prepared=cp.spawnSync(process.execPath,[script,temp],{encoding:'utf8'});
    assert.equal(prepared.status,0,prepared.stderr);
    assert.match(fs.readFileSync(path.join(temp,'index.html'),'utf8'),/get\('three'\)!=='cdn'/);
    assert.match(prepared.stdout,/mặc định dùng vendor\/three/);
  } finally { fs.rmSync(temp,{recursive:true,force:true}); }
});
```

## V246 Pages preparation is fail-closed, idempotent, and preserves the explicit CDN override

```javascript
test('V246 Pages preparation is fail-closed, idempotent, and preserves the explicit CDN override', () => {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'lylamlam-pages-idempotent-'));
  const script=path.join(root,'tools/prepare-pages-deploy.cjs');
  const original=fs.readFileSync(path.join(root,'index.html'),'utf8');
  const htmlPath=path.join(temp,'index.html');
  try {
    fs.writeFileSync(htmlPath,original);
    const before=fs.readFileSync(htmlPath,'utf8');
    const missing=cp.spawnSync(process.execPath,[script,temp],{encoding:'utf8'});
    assert.notEqual(missing.status,0);
    assert.equal(fs.readFileSync(htmlPath,'utf8'),before,'failure must not mutate deployment HTML');
    const vendor=path.join(temp,'vendor','three');
    for(const file of ['build/three.module.js','examples/jsm/loaders/GLTFLoader.js','examples/jsm/controls/OrbitControls.js']) {
      fs.mkdirSync(path.dirname(path.join(vendor,file)),{recursive:true});
      fs.writeFileSync(path.join(vendor,file),'export {};');
    }
    fs.writeFileSync(path.join(vendor,'LICENSE'),'fixture license');
    fs.writeFileSync(path.join(vendor,'package.json'),JSON.stringify({name:'three',version:'0.160.0'}));
    const first=cp.spawnSync(process.execPath,[script,temp],{encoding:'utf8'});
    assert.equal(first.status,0,first.stderr);
    const prepared=fs.readFileSync(htmlPath,'utf8');
    assert.match(prepared,/get\('three'\)!=='cdn'/);
    assert.match(prepared,/new URLSearchParams\(location\.search\)\.get\('three'\)!=='cdn'/);
    const second=cp.spawnSync(process.execPath,[script,temp],{encoding:'utf8'});
    assert.equal(second.status,0,second.stderr);
    assert.equal(fs.readFileSync(htmlPath,'utf8'),prepared,'running preparation twice must not change the result');
  } finally { fs.rmSync(temp,{recursive:true,force:true}); }
});
```

## V275 Pages deployment fails closed unless pinned Three.js is self-hosted

```javascript
test('V275 Pages deployment fails closed unless pinned Three.js is self-hosted', () => {
  const workflow=fs.readFileSync(path.join(root,'.github/workflows/deploy.yml'),'utf8');
  assert.match(workflow,/Fetch and stage pinned Three\.js for self-hosted deployment[\s\S]*?timeout-minutes: 3[\s\S]*?run: node tools\/fetch-vendor-three\.cjs/);
  assert.doesNotMatch(workflow,/continue-on-error:\s*true/,'vendor acquisition failure must stop deployment');
  assert.doesNotMatch(workflow,/CDN import-map mode as a fallback/,'deployment must not silently publish an externally dependent fallback');
  assert.match(workflow,/Prepare Pages to default to local Three\.js\s+run: node tools\/prepare-pages-deploy\.cjs/);
  assert.match(workflow,/node tools\/vendor-module-integrity\.cjs/,'self-hosted dependency graph must be validated before publication');
  assert.match(workflow,/node tools\/static-http-smoke\.cjs dist/,'the exact public artifact must pass HTTP smoke checks');
  const fetch=fs.readFileSync(path.join(root,'tools/fetch-vendor-three.cjs'),'utf8');
  assert.match(fetch,/three@0\.160\.0/);
  assert.doesNotMatch(fetch,/GITHUB_OUTPUT|fallback=true/,'the fetch script must not emit a machine-readable CDN fallback signal');
});
```

## V277 caches npm downloads across Pages runs to reduce repeated Three.js registry dependence

```javascript
test('V277 caches npm downloads across Pages runs to reduce repeated Three.js registry dependence', () => {
  const workflow = fs.readFileSync(path.join(root, '.github/workflows/deploy.yml'), 'utf8');
  assert.match(workflow, /Restore npm cache for pinned Three\.js acquisition[\s\S]*?uses: actions\/cache@v4[\s\S]*?path: ~\/.npm[\s\S]*?key: \${\{ runner\.os \}\}-three-0\.160\.0-\$\{\{ hashFiles\('tools\/fetch-vendor-three\.cjs'\) \}\}/);
  assert.match(workflow, /restore-keys:[\s\S]*?\$\{\{ runner\.os \}\}-three-0\.160\.0-/);
  assert.ok(workflow.indexOf('Restore npm cache for pinned Three.js acquisition') < workflow.indexOf('Fetch and stage pinned Three.js for self-hosted deployment'), 'cache must be restored before dependency acquisition');
  assert.doesNotMatch(workflow, /continue-on-error:\s*true/);
});
```

## V280 saves npm cache only after successful acquisition and skips immutable exact cache hits

```javascript
test('V280 saves npm cache only after successful acquisition and skips immutable exact cache hits', () => {
  const workflow = fs.readFileSync(path.join(root, '.github/workflows/deploy.yml'), 'utf8');
  const fetchIndex = workflow.indexOf('Fetch and stage pinned Three.js for self-hosted deployment');
  const saveIndex = workflow.indexOf('Save npm cache after successful Three.js acquisition');
  const prepareIndex = workflow.indexOf('Prepare Pages to default to local Three.js');
  assert.ok(fetchIndex >= 0 && saveIndex > fetchIndex && prepareIndex > saveIndex, 'cache save must follow acquisition and precede deployment preparation');
  const saveBlock = workflow.slice(saveIndex, prepareIndex);
  assert.match(workflow, /Restore npm cache for pinned Three\.js acquisition\s+id: npm-cache/, 'cache restore must expose its exact-hit status');
  assert.match(saveBlock, /if: success\(\) && steps\.npm-cache\.outputs\.cache-hit != 'true'/, 'save only a completed acquisition and do not overwrite an immutable exact-hit cache key');
  assert.doesNotMatch(saveBlock, /if: always\(\)/, 'a failed or partial acquisition must not create an immutable partial cache entry');
  assert.match(saveBlock, /uses: actions\/cache\/save@v4/);
  assert.match(saveBlock, /path: ~\/.npm/);
  assert.match(saveBlock, /key: \$\{\{ runner\.os \}\}-three-0\.160\.0-\$\{\{ hashFiles\('tools\/fetch-vendor-three\.cjs'\) \}\}/);
  assert.doesNotMatch(workflow, /continue-on-error:\s*true/);
});
```

## V276 npm network failures emit no fallback output and keep deployment fail-closed

```javascript
test('V276 npm network failures emit no fallback output and keep deployment fail-closed', () => {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'lylamlam-v275-network-classification-'));
  const bin=path.join(temp,'bin'); fs.mkdirSync(bin);
  const npm=path.join(bin,'npm');
  const output=path.join(temp,'github-output');
  const tool=path.join(root,'tools/fetch-vendor-three.cjs');
  const env={...process.env,PATH:`${bin}:${process.env.PATH}`,GITHUB_OUTPUT:output};
  try {
    fs.writeFileSync(npm,'#!/bin/sh\necho "npm ERR! code EAI_AGAIN" >&2\nexit 1\n',{mode:0o755});
    const result=cp.spawnSync(process.execPath,[tool],{encoding:'utf8',env});
    assert.notEqual(result.status,0);
    assert.equal(fs.existsSync(output),false,'network failures must not emit a fallback output or authorize CDN deployment');
    assert.match(result.stderr,/Bước triển khai sẽ dừng/,'the operator receives an explicit fail-closed hint');
    const workflow=fs.readFileSync(path.join(root,'.github/workflows/deploy.yml'),'utf8');
    assert.doesNotMatch(workflow,/steps\.vendor\.outputs\.fallback/,'workflow must not convert a network failure into a successful CDN deployment');
  } finally { fs.rmSync(temp,{recursive:true,force:true}); }
});
```

## V262 Pages preparation validates the import map before any HTML mutation

```javascript
test('V262 Pages preparation validates the import map before any HTML mutation', () => {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'lylamlam-v262-pages-map-'));
  const script=path.join(root,'tools/prepare-pages-deploy.cjs');
  const htmlPath=path.join(temp,'index.html');
  const original=fs.readFileSync(path.join(root,'index.html'),'utf8')
    .replace("'./vendor/three/'", "'./vendor/three-missing/'");
  try {
    fs.writeFileSync(htmlPath,original);
    const vendor=path.join(temp,'vendor','three');
    for(const file of ['build/three.module.js','examples/jsm/loaders/GLTFLoader.js','examples/jsm/controls/OrbitControls.js']) {
      fs.mkdirSync(path.dirname(path.join(vendor,file)),{recursive:true});
      fs.writeFileSync(path.join(vendor,file),'export {};');
    }
    fs.writeFileSync(path.join(vendor,'LICENSE'),'fixture license');
    fs.writeFileSync(path.join(vendor,'package.json'),JSON.stringify({name:'three',version:'0.160.0'}));
    const result=cp.spawnSync(process.execPath,[script,temp],{encoding:'utf8'});
    assert.notEqual(result.status,0,'invalid import-map paths must be rejected');
    assert.match(result.stderr,/import map sau chuẩn bị thiếu đường dẫn local hoặc CDN/);
    assert.equal(fs.readFileSync(htmlPath,'utf8'),original,'candidate validation failure must not mutate index.html');
    assert.equal(fs.readdirSync(temp).some(name=>name.startsWith('.index.html-pages-')),false,'no abandoned staged HTML should remain');
  } finally { fs.rmSync(temp,{recursive:true,force:true}); }
});
```

## V281 workflow_dispatch supports a repository-supplied pinned Three.js tarball

```javascript
test('V281 workflow_dispatch supports a repository-supplied pinned Three.js tarball', () => {
  const workflow = fs.readFileSync(path.join(root, '.github/workflows/deploy.yml'), 'utf8');
  assert.match(workflow, /workflow_dispatch:[\s\S]*?three_tarball_path:[\s\S]*?type: string[\s\S]*?three_tarball_sha512:[\s\S]*?type: string/);
  assert.match(workflow, /THREE_TARBALL: \$\{\{ inputs\.three_tarball_path \}\}/);
  assert.match(workflow, /THREE_TARBALL_SHA512: \$\{\{ inputs\.three_tarball_sha512 \}\}/);
  assert.match(workflow, /THREE_TARBALL_REQUIRE_SHA512: "1"/);
  const tool = fs.readFileSync(path.join(root, 'tools/fetch-vendor-three.cjs'), 'utf8');
  assert.match(tool, /THREE_TARBALL_REQUIRE_SHA512/);
  assert.match(tool, /SHA-512 của THREE_TARBALL không khớp/);
});
```

## V270 GitHub Pages workflow uploads the isolated dist artifact, not the repository root

```javascript
test('V270 GitHub Pages workflow uploads the isolated dist artifact, not the repository root', () => {
  const workflow = fs.readFileSync(path.join(root, '.github/workflows/deploy.yml'), 'utf8');
  assert.match(workflow, /node tools\/prepare-pages-artifact\.cjs dist/);
  assert.match(workflow, /uses: actions\/upload-pages-artifact@v3[\s\S]*?path: dist/);
  assert.doesNotMatch(workflow, /uses: actions\/upload-pages-artifact@v3[\s\S]*?path: \./);
});
```

## V274 runs the HTTP smoke test against the assembled Pages artifact

```javascript
test('V274 runs the HTTP smoke test against the assembled Pages artifact', () => {
  const smoke = fs.readFileSync(path.join(root, 'tools/static-http-smoke.cjs'), 'utf8');
  assert.match(smoke, /path\.resolve\(process\.argv\[2\] \|\| path\.join\(__dirname, '\.\.'\)\)/);
  const workflow = fs.readFileSync(path.join(root, '.github/workflows/deploy.yml'), 'utf8');
  assert.match(workflow, /Assemble minimal public Pages artifact[\s\S]*?prepare-pages-artifact\.cjs dist[\s\S]*?Smoke-test the exact Pages artifact over HTTP[\s\S]*?static-http-smoke\.cjs dist[\s\S]*?Upload static site/);
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'lylamlam-v274-artifact-smoke-'));
  const output = path.join(temp, 'dist');
  try {
    let result = cp.spawnSync(process.execPath, [path.join(root, 'tools/prepare-pages-artifact.cjs'), output], { encoding: 'utf8', timeout: 15000 });
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    result = cp.spawnSync(process.execPath, [path.join(root, 'tools/static-http-smoke.cjs'), output], { encoding: 'utf8', timeout: 15000 });
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    assert.match(result.stdout, /PASS HTTP 200 index\.html/);
    assert.match(result.stdout, /PASS HTTP 200 lam-default\.glb/);
    assert.match(result.stdout, /PASS HTTP 403 cho đường dẫn thoát khỏi thư mục gốc/);
  } finally { fs.rmSync(temp, { recursive: true, force: true }); }
});
```

## V270 Pages artifact contains runtime assets but excludes development tooling

```javascript
test('V270 Pages artifact contains runtime assets but excludes development tooling', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'lylamlam-pages-artifact-'));
  const output = path.join(temp, 'public-site');
  try {
    const result = cp.spawnSync(process.execPath, [path.join(root, 'tools/prepare-pages-artifact.cjs'), output], { encoding: 'utf8' });
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    for (const file of ['index.html', 'module.mjs', 'lam-default.glb', 'expression-baseline-cases-v1.json', '.nojekyll', 'avatar_expression_motion.js']) assert.ok(fs.existsSync(path.join(output, file)), `missing runtime file ${file}`);
    for (const file of ['tests', 'tools', 'README-VI.txt', 'TESTING-VI.txt', 'VERSION.txt', 'SHA256SUMS.txt']) assert.ok(!fs.existsSync(path.join(output, file)), `unexpected public file ${file}`);
    assert.match(result.stdout, /cạnh import tương đối đã xác minh/);
  } finally { fs.rmSync(temp, { recursive: true, force: true }); }
});
```

## V271 Pages artifact recursively validates nested vendor imports and rejects symlinks

```javascript
test('V271 Pages artifact recursively validates nested vendor imports and rejects symlinks', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'lylamlam-v271-artifact-'));
  const source = path.join(temp, 'source');
  const output = path.join(temp, 'public-site');
  const toolDir = path.join(source, 'tools');
  try {
    fs.mkdirSync(toolDir, { recursive: true });
    for (const file of ['index.html', 'module.mjs', 'lam-default.glb', 'expression-baseline-cases-v1.json', '.nojekyll']) {
      fs.copyFileSync(path.join(root, file), path.join(source, file));
    }
    for (const name of fs.readdirSync(root)) {
      if (/\.(?:js|mjs)$/.test(name) && fs.statSync(path.join(root, name)).isFile()) fs.copyFileSync(path.join(root, name), path.join(source, name));
    }
    fs.copyFileSync(path.join(root, 'tools/prepare-pages-artifact.cjs'), path.join(toolDir, 'prepare-pages-artifact.cjs'));
    const nested = path.join(source, 'vendor/three/examples/jsm/loaders');
    fs.mkdirSync(nested, { recursive: true });
    fs.writeFileSync(path.join(source, 'vendor/three/build-placeholder.js'), 'export const ok = true;');
    fs.writeFileSync(path.join(nested, 'GLTFLoader.js'), "import './missing-helper.js'; export class GLTFLoader {};");
    let result = cp.spawnSync(process.execPath, [path.join(toolDir, 'prepare-pages-artifact.cjs'), output], { encoding: 'utf8', timeout: 15000 });
    assert.notEqual(result.status, 0, 'missing nested vendor import must fail artifact assembly');
    assert.ok(result.stderr.includes('vendor/three/examples/jsm/loaders/GLTFLoader.js: import không có trong artifact'), result.stderr);
    assert.equal(fs.existsSync(output), false, 'failed artifact must not publish destination');

    fs.writeFileSync(path.join(nested, 'missing-helper.js'), 'export const helper = true;');
    result = cp.spawnSync(process.execPath, [path.join(toolDir, 'prepare-pages-artifact.cjs'), output], { encoding: 'utf8', timeout: 15000 });
    assert.equal(result.status, 0, `${result.stdout}\\n${result.stderr}`);
    assert.match(result.stdout, /cạnh import tương đối đã xác minh/);
    assert.ok(fs.existsSync(path.join(output, 'vendor/three/examples/jsm/loaders/missing-helper.js')));

    const outside = path.join(temp, 'outside-secret.js');
    fs.writeFileSync(outside, 'export const secret = true;');
    fs.symlinkSync(outside, path.join(source, 'vendor/three/examples/jsm/loaders/linked-secret.js'));
    result = cp.spawnSync(process.execPath, [path.join(toolDir, 'prepare-pages-artifact.cjs'), output], { encoding: 'utf8', timeout: 15000 });
    assert.notEqual(result.status, 0, 'symlinks must be rejected in the public artifact');
    assert.match(result.stderr, /không chấp nhận symbolic link/);
    assert.ok(fs.existsSync(path.join(output, 'vendor/three/examples/jsm/loaders/missing-helper.js')), 'previous valid artifact must remain intact after failure');
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
});
```

## V272 Pages artifact rejects root-level symlink inputs without replacing a valid artifact

```javascript
test('V272 Pages artifact rejects root-level symlink inputs without replacing a valid artifact', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'lylamlam-v272-root-symlink-'));
  const source = path.join(temp, 'source');
  const output = path.join(temp, 'public-site');
  try {
    fs.mkdirSync(source, { recursive: true });
    for (const file of ['index.html', 'module.mjs', 'lam-default.glb', 'expression-baseline-cases-v1.json', '.nojekyll']) {
      fs.copyFileSync(path.join(root, file), path.join(source, file));
    }
    for (const name of fs.readdirSync(root)) {
      if (/\.(?:js|mjs)$/.test(name) && fs.lstatSync(path.join(root, name)).isFile()) fs.copyFileSync(path.join(root, name), path.join(source, name));
    }
    const toolDir = path.join(source, 'tools');
    fs.mkdirSync(toolDir, { recursive: true });
    fs.copyFileSync(path.join(root, 'tools/prepare-pages-artifact.cjs'), path.join(toolDir, 'prepare-pages-artifact.cjs'));
    let result = cp.spawnSync(process.execPath, [path.join(toolDir, 'prepare-pages-artifact.cjs'), output], { encoding: 'utf8', timeout: 15000 });
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    const stableFile = path.join(output, 'index.html');
    const stableHash = require('node:crypto').createHash('sha256').update(fs.readFileSync(stableFile)).digest('hex');

    const external = path.join(temp, 'external.js');
    fs.writeFileSync(external, 'export const external = true;');
    fs.symlinkSync(external, path.join(source, 'root-linked-module.js'));
    result = cp.spawnSync(process.execPath, [path.join(toolDir, 'prepare-pages-artifact.cjs'), output], { encoding: 'utf8', timeout: 15000 });
    assert.notEqual(result.status, 0, 'root-level symlink input must be rejected');
    assert.match(result.stderr, /không chấp nhận symbolic link ở thư mục gốc/);
    assert.equal(require('node:crypto').createHash('sha256').update(fs.readFileSync(stableFile)).digest('hex'), stableHash, 'previous valid artifact remains intact');
    assert.equal(fs.existsSync(path.join(output, 'root-linked-module.js')), false);
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
});
```
