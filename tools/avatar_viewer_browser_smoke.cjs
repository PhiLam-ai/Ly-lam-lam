const { chromium } = require('playwright');
const { spawn } = require('node:child_process');

(async () => {
  const server = spawn('python3', ['-m', 'http.server', '8765', '--bind', '127.0.0.1'], {
    stdio: 'ignore',
    detached: false
  });
  let browser;
  try {
    await new Promise((resolve, reject) => {
      let attempts = 0;
      const poll = async () => {
        attempts++;
        try {
          const response = await fetch('http://127.0.0.1:8765/');
          if (response.ok) return resolve();
        } catch {}
        if (attempts >= 40) return reject(new Error('Local preview server did not start'));
        setTimeout(poll, 250);
      };
      poll();
    });

    browser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl']
    });
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    const pageErrors = [];
    const badResponses = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('response', response => {
      if (response.status() >= 400 && new URL(response.url()).origin === 'http://127.0.0.1:8765') {
        badResponses.push(`${response.status()} ${response.url()}`);
      }
    });

    await page.goto('http://127.0.0.1:8765/?diagnostics=1', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForFunction(() => {
      const status = document.querySelector('#status')?.textContent || '';
      return status.includes('Avatar đã tải thành công') ||
             status.includes('Tải avatar thất bại') ||
             status.includes('không có hình học hiển thị') ||
             status.includes('Không tìm thấy tài nguyên');
    }, { timeout: 45000 });

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
      glbResourceRequested: performance.getEntriesByType('resource').some(r => r.name.includes('lam-default.glb'))
    }));

    console.log('BROWSER_RESULT ' + JSON.stringify(result));
    if (!result.diagnosticsVisible) throw new Error('Diagnostics panel did not appear for diagnostics=1');
    if (result.canvasCount !== 1 || !result.canvasRect || result.canvasRect.width < 100 || result.canvasRect.height < 100) {
      throw new Error('WebGL canvas is missing or too small');
    }
    if (!result.glbResourceRequested) throw new Error('Browser did not request lam-default.glb');
    if (!result.status.includes('Avatar đã tải thành công')) throw new Error('Avatar did not reach loaded state: ' + result.status);
    if (pageErrors.length) throw new Error('Browser page errors: ' + pageErrors.join(' | '));
    if (badResponses.length) throw new Error('Local asset HTTP errors: ' + badResponses.join(' | '));
    console.log('PASS: browser loaded GLB and viewer reached avatar-loaded state');
  } catch (error) {
    console.error('FAIL: browser smoke test:', error.stack || error);
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
})();
