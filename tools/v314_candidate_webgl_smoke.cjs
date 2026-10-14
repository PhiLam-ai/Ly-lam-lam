'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
const { PNG } = require('pngjs');

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
    visualFraming: null,
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
        activeAnimationName: window.__lyLamActiveAnimationName || '',
        animationTime: Number(window.__lyLamAnimationTime || 0),
        viewport: { width: window.innerWidth, height: window.innerHeight }
      };
    });
    report.avatarDiagnostics = await page.evaluate(() => window.__lyLamAvatarDiagnostics || null);
    await page.screenshot({ path: path.join(evidenceDir, 'v314-candidate-browser.png'), fullPage: true });
    const canvasPath = path.join(evidenceDir, 'v314-candidate-canvas.png');
    await page.locator('#stage canvas').screenshot({ path: canvasPath });
    const canvasPng = PNG.sync.read(fs.readFileSync(canvasPath));
    const rowCounts = new Array(canvasPng.height).fill(0);
    const background = [16, 24, 39];
    const threshold = 18;
    for (let y = 0; y < canvasPng.height; y++) {
      for (let x = 0; x < canvasPng.width; x++) {
        const index = (y * canvasPng.width + x) * 4;
        const delta = Math.max(
          Math.abs(canvasPng.data[index] - background[0]),
          Math.abs(canvasPng.data[index + 1] - background[1]),
          Math.abs(canvasPng.data[index + 2] - background[2])
        );
        if (canvasPng.data[index + 3] > 16 && delta > threshold) rowCounts[y]++;
      }
    }
    // Exclude rows covered by the floating quick-controls and status card.
    // The old full-image row coverage incorrectly passed when only the lower legs
    // were visible because UI chrome itself supplied foreground pixels.
    const safeTop = Math.min(108, Math.floor(canvasPng.height * 0.13));
    const safeBottom = Math.max(safeTop + 1, canvasPng.height - 96);
    const minPixelsInRow = Math.max(3, Math.floor(canvasPng.width * 0.015));
    const activeRows = rowCounts.map((count, index) => ({count, index}))
      .filter(row => row.index >= safeTop && row.index < safeBottom && row.count >= minPixelsInRow);
    const topRow = activeRows.length ? activeRows[0].index : null;
    const bottomRow = activeRows.length ? activeRows[activeRows.length - 1].index : null;
    const safeCoverage = topRow === null ? 0 : (bottomRow - topRow + 1) / (safeBottom - safeTop);
    const allActiveRows = rowCounts.map((count, index) => ({count, index})).filter(row => row.count >= minPixelsInRow);
    const rawTopRow = allActiveRows.length ? allActiveRows[0].index : null;
    const rawBottomRow = allActiveRows.length ? allActiveRows[allActiveRows.length - 1].index : null;
    const rawCoverage = rawTopRow === null ? 0 : (rawBottomRow - rawTopRow + 1) / canvasPng.height;
    report.visualFraming = {
      canvas: { width: canvasPng.width, height: canvasPng.height },
      rawTopRow, rawBottomRow,
      rawVerticalCoverage: Number(rawCoverage.toFixed(4)),
      ignoredOverlayRows: { topEndExclusive: safeTop, bottomStartInclusive: safeBottom },
      topRow, bottomRow,
      safeAreaVerticalCoverage: Number(safeCoverage.toFixed(4)),
      thresholdRGBDelta: threshold,
      minPixelsInRow,
      classification: safeCoverage >= 0.6 ? 'VISIBLE_AVATAR_IN_SAFE_AREA' : 'LIKELY_CROPPED_OR_OFF_CENTER',
      note: 'Safe-area pixel heuristic excludes floating buttons/status UI; combine with projected model bounds and inspect the screenshot.'
    };

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
    if (!report.avatarDiagnostics || !report.avatarDiagnostics.framing) {
      throw new Error('Viewer did not expose projected avatar bounds for camera validation.');
    }
    const projected = report.avatarDiagnostics.framing;
    if (!projected.fitsNdc || projected.verticalCoverage < 0.58 || projected.verticalCoverage > 0.80 ||
        Math.abs(projected.verticalCenter) > 0.22) {
      throw new Error('Projected model bounds are cropped or off-center: ' + JSON.stringify(projected));
    }
    if (report.visualFraming.safeAreaVerticalCoverage < 0.6) {
      throw new Error('Actual canvas foreground does not fill the unobstructed safe area: ' + JSON.stringify(report.visualFraming));
    }
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
    console.log('VISUAL_FRAMING_DIAGNOSTIC=' + JSON.stringify(report.visualFraming));
  }
})().catch(error => {
  console.error(error.stack || error);
  process.exit(1);
});
