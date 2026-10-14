'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');

const appRoot = path.resolve(__dirname, '..');
const serverScript = path.join(__dirname, 'serve-preview.cjs');
const evidenceDir = process.env.STARTUP_EVIDENCE_DIR || path.join(os.tmpdir(), 'lylamlam-windows-startup');
fs.mkdirSync(evidenceDir, { recursive: true });

function startLocalServer() {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [
      serverScript, '--host', '127.0.0.1', '--port', '0', '--root', appRoot, '--three', 'local'
    ], { cwd: appRoot, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    let finished = false;
    const timer = setTimeout(() => {
      if (finished) return;
      finished = true;
      child.kill();
      reject(new Error('Local preview server did not announce readiness within 10 seconds.\n' + stdout + '\n' + stderr));
    }, 10000);
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', chunk => {
      stdout += chunk;
      const match = stdout.match(/URL: http:\/\/127\.0\.0\.1:(\d+)\/\?three=local/);
      if (!match || finished) return;
      finished = true;
      clearTimeout(timer);
      resolve({ child, base: 'http://127.0.0.1:' + match[1], getLogs: () => ({ stdout, stderr }) });
    });
    child.stderr.on('data', chunk => { stderr += chunk; });
    child.once('error', error => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      reject(new Error('Unable to start the local server: ' + error.message));
    });
    child.once('exit', (code, signal) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      reject(new Error('Local preview server exited before readiness (code=' + code + ', signal=' + signal + ').\n' + stdout + '\n' + stderr));
    });
  });
}

(async () => {
  let server = null;
  let browser = null;
  const report = {
    platform: process.platform,
    node: process.version,
    runtimeMode: 'local Three.js assets',
    appRoot,
    state: null,
    assetResponses: [],
    pageErrors: [],
    consoleErrors: [],
    failedRequests: [],
    serverLogs: null
  };
  let fatal = null;
  try {
    server = await startLocalServer();
    browser = await chromium.launch({
      headless: true,
      args: ['--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist']
    });
    const page = await browser.newPage({ viewport: { width: 1365, height: 900 }, deviceScaleFactor: 1 });
    page.on('pageerror', error => report.pageErrors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') report.consoleErrors.push(message.text());
    });
    page.on('requestfailed', request => {
      report.failedRequests.push({
        url: request.url(),
        error: request.failure() ? request.failure().errorText : 'unknown'
      });
    });
    page.on('response', response => {
      const url = new URL(response.url());
      if (url.pathname.endsWith('/lam-default.glb') ||
          url.pathname.endsWith('/three.module.js') ||
          url.pathname.endsWith('/GLTFLoader.js') ||
          url.pathname.endsWith('/OrbitControls.js')) {
        report.assetResponses.push({ path: url.pathname, status: response.status() });
      }
    });

    const response = await page.goto(server.base + '/?three=local', {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });
    if (!response || !response.ok()) throw new Error('App entry page did not return HTTP success.');
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
    await page.screenshot({ path: path.join(evidenceDir, 'windows-startup.png'), fullPage: true });

    if (!report.state.booted || report.state.failed) throw new Error('App did not boot cleanly: ' + report.state.status);
    if (!report.state.rendererReady || report.state.canvasCount !== 1 || !report.state.webgl) {
      throw new Error('WebGL renderer/canvas is not ready: ' + JSON.stringify(report.state));
    }
    for (const suffix of ['/lam-default.glb', '/vendor/three/build/three.module.js',
                          '/vendor/three/examples/jsm/loaders/GLTFLoader.js',
                          '/vendor/three/examples/jsm/controls/OrbitControls.js']) {
      if (!report.assetResponses.some(item => item.path.endsWith(suffix) && item.status === 200)) {
        throw new Error('Required local asset did not return HTTP 200: ' + suffix);
      }
    }
    if (report.pageErrors.length) throw new Error('JavaScript page errors: ' + report.pageErrors.join(' | '));
    if (report.failedRequests.length) throw new Error('Failed browser requests: ' + JSON.stringify(report.failedRequests));
    if (report.consoleErrors.length) throw new Error('Browser console errors: ' + report.consoleErrors.join(' | '));
    report.status = 'PASS';
  } catch (error) {
    fatal = error;
    report.status = 'FAIL';
    report.error = error && error.stack ? error.stack : String(error);
  } finally {
    if (server) report.serverLogs = server.getLogs();
    fs.writeFileSync(path.join(evidenceDir, 'windows-startup-report.json'), JSON.stringify(report, null, 2));
    if (browser) await browser.close().catch(() => {});
    if (server && server.child.exitCode === null) server.child.kill();
  }
  console.log('WINDOWS_STARTUP_REPORT=' + JSON.stringify(report));
  if (fatal) {
    console.error(fatal.stack || fatal);
    process.exitCode = 1;
  } else {
    console.log('PASS: Windows-hosted Chromium booted the application, rendered a WebGL canvas, and loaded GLB plus bundled Three.js modules.');
    console.log('LIMIT: this is Windows CI with headless Chromium, not yet a manual Chrome run on the user laptop.');
  }
})().catch(error => {
  console.error(error.stack || error);
  process.exit(1);
});
