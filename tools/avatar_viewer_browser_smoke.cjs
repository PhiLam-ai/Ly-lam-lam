const { chromium } = require('playwright');
const { spawn } = require('node:child_process');

(async () => {
  const server = spawn('python3', ['-m', 'http.server', '8765', '--bind', '127.0.0.1'], { stdio: 'ignore' });
  let browser;
  try {
    await new Promise((resolve, reject) => {
      let attempts = 0;
      const poll = async () => {
        try {
          const response = await fetch('http://127.0.0.1:8765/');
          if (response.ok) return resolve();
        } catch {}
        if (++attempts >= 40) return reject(new Error('Local preview server did not start'));
        setTimeout(poll, 250);
      };
      poll();
    });

    browser = await chromium.launch({ headless: true, args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl'] });
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    const pageErrors = [];
    const consoleErrors = [];
    const failedRequests = [];
    const badResponses = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
    page.on('requestfailed', request => failedRequests.push(request.url() + ' :: ' + (request.failure()?.errorText || 'request failed')));
    page.on('response', response => {
      if (response.status() >= 400) badResponses.push(response.status() + ' ' + response.url());
    });

    await page.goto('http://127.0.0.1:8765/?diagnostics=1', { waitUntil: 'domcontentloaded', timeout: 30000 });
    // Wait long enough for either success or the viewer's 15-second diagnostic timeout.
    await page.waitForTimeout(22000);

    const result = await page.evaluate(() => ({
      status: document.querySelector('#status')?.textContent || '',
      canvasCount: document.querySelectorAll('#stage canvas').length,
      canvasRect: (() => {
        const canvas = document.querySelector('#stage canvas');
        if (!canvas) return null;
        const r = canvas.getBoundingClientRect();
        return { width: r.width, height: r.height };
      })(),
      diagnosticsVisible: getComputedStyle(document.querySelector('#diagnostics')).display !== 'none',
      glbResourceRequested: performance.getEntriesByType('resource').some(r => r.name.includes('lam-default.glb')),
      stageHasChildren: document.querySelector('#stage')?.children.length > 0
    }));
    console.log('BROWSER_RESULT ' + JSON.stringify({ ...result, pageErrors, consoleErrors, failedRequests, badResponses }));

    const debugState = await page.evaluate(() => window.__avatarViewerDebug || null);
    console.log('AVATAR_DEBUG ' + JSON.stringify(debugState));
    const failures = [];
    if (!result.diagnosticsVisible) failures.push('diagnostics panel did not appear for diagnostics=1');
    if (result.canvasCount !== 1 || !result.canvasRect || result.canvasRect.width < 100 || result.canvasRect.height < 100) failures.push('WebGL canvas missing or too small');
    if (!result.glbResourceRequested) failures.push('browser did not request lam-default.glb');
    if (!debugState?.ready) failures.push('GLTFLoader success callback did not confirm avatar readiness; debug=' + JSON.stringify(debugState));
    if (!debugState || debugState.meshCount < 1) failures.push('loaded GLB has no mesh objects; debug=' + JSON.stringify(debugState));
    if (!debugState || debugState.morphCount < 1) failures.push('loaded GLB has no morph bindings; debug=' + JSON.stringify(debugState));
    if (!debugState || Math.abs(debugState.bounds.y - 1.6) > 0.02) failures.push('avatar height is not normalized to 1.60 m; debug=' + JSON.stringify(debugState));
    if (pageErrors.length) failures.push('page errors: ' + pageErrors.join(' | '));
    if (badResponses.some(x => x.includes('127.0.0.1:8765'))) failures.push('local asset HTTP errors: ' + badResponses.filter(x => x.includes('127.0.0.1:8765')).join(' | '));
    if (failures.length) {
      console.error('FAIL: ' + failures.join('\n'));
      process.exitCode = 1;
    } else {
      console.log('PASS: Chromium created canvas, requested GLB, and viewer reached avatar-loaded state');
    }
  } catch (error) {
    console.error('FAIL: browser smoke test setup:', error.stack || error);
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
})();
