'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');

const appRoot = process.env.V314_VIEWER_ROOT ? path.resolve(process.env.V314_VIEWER_ROOT) : '';
const evidenceDir = process.env.V314_VIEWER_EVIDENCE_DIR || path.resolve('artifacts/v314-browser-test');
const serverScript = appRoot ? path.join(appRoot, 'tools', 'serve-preview.cjs') : '';
fs.mkdirSync(evidenceDir, { recursive: true });

function requireFile(file, label) {
  if (!file || !fs.existsSync(file)) throw new Error('Missing ' + label + ': ' + (file || '(path not set)'));
}
function startServer() {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [
      serverScript, '--host', '127.0.0.1', '--port', '0', '--root', appRoot, '--three', 'local'
    ], { cwd: appRoot, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '', ready = false;
    const timer = setTimeout(() => {
      if (ready) return;
      child.kill();
      reject(new Error('Candidate preview server did not start in 10 seconds.\n' + stdout + '\n' + stderr));
    }, 10000);
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', chunk => {
      stdout += chunk;
      const match = stdout.match(/URL: http:\/\/127\.0\.0\.1:(\d+)\/\?three=local/);
      if (!match || ready) return;
      ready = true;
      clearTimeout(timer);
      resolve({ child, base: 'http://127.0.0.1:' + match[1], logs: () => ({ stdout, stderr }) });
    });
    child.stderr.on('data', chunk => { stderr += chunk; });
    child.once('error', error => {
      if (!ready) {
        clearTimeout(timer);
        reject(error);
      }
    });
    child.once('exit', (code, signal) => {
      if (!ready) {
        clearTimeout(timer);
        reject(new Error('Preview server exited before readiness: ' + code + '/' + signal + '\n' + stdout + '\n' + stderr));
      }
    });
  });
}

(async () => {
  requireFile(appRoot, 'viewer root');
  requireFile(serverScript, 'preview server');
  requireFile(path.join(appRoot, 'index.html'), 'viewer HTML');
  requireFile(path.join(appRoot, 'lam-default.glb'), 'candidate GLB');
  requireFile(path.join(appRoot, 'vendor', 'three', 'build', 'three.module.js'), 'bundled Three.js');
  const report = {
    platform: process.platform,
    appRoot,
    state: null,
    glbResponses: [],
    requiredLocalAssetResponses: [],
    pageErrors: [],
    consoleErrors: [],
    failedRequests: [],
    ignoredBenignAborts: [],
    serverLogs: null
  };
  let server = null, browser = null, fatal = null;
  try {
    server = await startServer();
    browser = await chromium.launch({
      headless: true,
      args: ['--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist']
    });
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
    page.on('pageerror', error => report.pageErrors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') report.consoleErrors.push(message.text());
    });
    page.on('requestfailed', request => report.failedRequests.push({
      url: request.url(),
      error: request.failure() ? request.failure().errorText : 'unknown'
    }));
    page.on('response', response => {
      const url = new URL(response.url());
      if (url.pathname.endsWith('/lam-default.glb')) report.glbResponses.push({ status: response.status(), url: response.url() });
      if (url.pathname.endsWith('/three.module.js') ||
          url.pathname.endsWith('/GLTFLoader.js') ||
          url.pathname.endsWith('/OrbitControls.js')) {
        report.requiredLocalAssetResponses.push({ path: url.pathname, status: response.status() });
      }
    });
    const response = await page.goto(server.base + '/?three=local', { waitUntil: 'domcontentloaded', timeout: 30000 });
    if (!response || !response.ok()) throw new Error('Viewer entry page did not return HTTP success.');
    await page.waitForFunction(
      () => window.__lyLamAppBooted === true || window.__lyLamBootFailed === true,
      null,
      { timeout: 60000 }
    );
    await page.waitForTimeout(800);
    report.state = await page.evaluate(() => {
      const canvas = document.querySelector('#stage canvas');
      let webgl = false;
      try { webgl = !!canvas && (!!canvas.getContext('webgl2') || !!canvas.getContext('webgl')); } catch (_) {}
      return {
        booted: window.__lyLamAppBooted === true,
        failed: window.__lyLamBootFailed === true,
        rendererReady: window.__lyLamRendererReady === true,
        canvasCount: document.querySelectorAll('#stage canvas').length,
        webgl,
        status: document.querySelector('#status-message')?.textContent ||
                document.querySelector('#status')?.textContent || '',
        viewport: { width: window.innerWidth, height: window.innerHeight }
      };
    });
    await page.screenshot({ path: path.join(evidenceDir, 'v314-candidate-browser.png'), fullPage: true });

    if (!report.state.booted || report.state.failed) throw new Error('Candidate viewer did not boot: ' + report.state.status);
    if (!report.state.rendererReady || report.state.canvasCount !== 1 || !report.state.webgl) {
      throw new Error('Candidate viewer WebGL is not ready: ' + JSON.stringify(report.state));
    }
    if (!report.state.status.includes('12 morph')) throw new Error('Expected 12 morph targets were not reported: ' + report.state.status);
    if (!report.glbResponses.some(item => item.status === 200)) throw new Error('Candidate GLB did not return HTTP 200.');
    for (const suffix of ['/three.module.js', '/GLTFLoader.js', '/OrbitControls.js']) {
      if (!report.requiredLocalAssetResponses.some(item => item.path.endsWith(suffix) && item.status === 200)) {
        throw new Error('Required bundled Three.js asset missing: ' + suffix);
      }
    }
    const fatalRequests = [];
    for (const item of report.failedRequests) {
      const benign = item.error === 'net::ERR_ABORTED' &&
        new URL(item.url).pathname.endsWith('/lam-default.glb') &&
        report.glbResponses.some(responseItem => responseItem.status === 200) &&
        report.state.booted && report.state.rendererReady &&
        report.state.status.includes('Mô hình đã tải');
      if (benign) report.ignoredBenignAborts.push(item);
      else fatalRequests.push(item);
    }
    if (fatalRequests.length) throw new Error('Failed viewer requests: ' + JSON.stringify(fatalRequests));
    if (report.pageErrors.length) throw new Error('Browser page errors: ' + report.pageErrors.join(' | '));
    if (report.consoleErrors.length) throw new Error('Browser console errors: ' + report.consoleErrors.join(' | '));
    report.status = 'PASS_BROWSER_WEBGL_CANDIDATE_ONLY';
  } catch (error) {
    fatal = error;
    report.status = 'FAIL';
    report.error = error && error.stack ? error.stack : String(error);
  } finally {
    if (server) report.serverLogs = server.logs();
    fs.writeFileSync(path.join(evidenceDir, 'v314-candidate-browser-report.json'), JSON.stringify(report, null, 2));
    if (browser) await browser.close().catch(() => {});
    if (server && server.child.exitCode === null) server.child.kill();
  }
  console.log('V314_CANDIDATE_BROWSER_REPORT=' + JSON.stringify(report));
  if (fatal) {
    console.error(fatal.stack || fatal);
    process.exitCode = 1;
  } else {
    console.log('PASS: candidate GLB loaded in mobile-sized Chromium viewport with WebGL and all 12 morphs reported.');
  }
})().catch(error => {
  console.error(error.stack || error);
  process.exit(1);
});
