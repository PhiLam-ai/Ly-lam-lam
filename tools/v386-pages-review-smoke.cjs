const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const BASE = process.env.LLL_REVIEW_URL || 'https://philam-ai.github.io/Ly-lam-lam/review-v386/';
const REVIEW_URL = new URL(BASE.endsWith('/') ? BASE : BASE + '/');
const APP_URL = new URL('./v312-work/index.html?three=local', REVIEW_URL);
const ARTIFACT_DIR = process.env.LLL_ARTIFACT_DIR || 'artifacts';
const reportPath = path.join(ARTIFACT_DIR, 'v386-https-review-smoke.json');
const screenshotPath = path.join(ARTIFACT_DIR, 'v386-https-review-smoke.png');

(async () => {
  const report = {
    test: 'V386 published HTTPS preview — mobile Chromium smoke test',
    reviewUrl: REVIEW_URL.href,
    appUrl: APP_URL.href,
    viewport: { width: 390, height: 844, isMobile: true, hasTouch: true },
    status: 'FAIL',
    checks: {},
    pageErrors: [],
    consoleErrors: [],
    failedRequests: [],
    modelResponses: [],
    localThreeResponses: [],
    externalThreeRequests: [],
  };
  let browser;
  try {
    browser = await chromium.launch({
      headless: true,
      args: ['--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist'],
    });
    const page = await browser.newPage({
      viewport: { width: 390, height: 844 },
      deviceScaleFactor: 2,
      isMobile: true,
      hasTouch: true,
    });
    page.on('pageerror', error => report.pageErrors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') report.consoleErrors.push(message.text());
    });
    page.on('requestfailed', request => report.failedRequests.push({
      url: request.url(),
      error: request.failure()?.errorText || 'unknown',
    }));
    page.on('request', request => {
      if (request.url().includes('cdn.jsdelivr.net') || request.url().includes('unpkg.com')) report.externalThreeRequests.push(request.url());
    });
    page.on('response', response => {
      const url = new URL(response.url());
      if (url.pathname.endsWith('/lam-default.glb')) report.modelResponses.push({ url: response.url(), status: response.status() });
      if (
        url.pathname.endsWith('/vendor/three/build/three.module.js') ||
        url.pathname.endsWith('/vendor/three/examples/jsm/loaders/GLTFLoader.js') ||
        url.pathname.endsWith('/vendor/three/examples/jsm/controls/OrbitControls.js')
      ) report.localThreeResponses.push({ url: response.url(), status: response.status() });
    });

    const wrapperResponse = await page.goto(REVIEW_URL.href, { waitUntil: 'domcontentloaded', timeout: 45000 });
    if (!wrapperResponse || !wrapperResponse.ok()) throw new Error('V386 review landing page did not return HTTP 200.');
    const href = await page.locator('a').first().getAttribute('href');
    report.checks.wrapperHttp200 = true;
    report.checks.wrapperLink = href;
    if (href !== './v312-work/index.html?three=local') throw new Error('Review landing page link is unexpected: ' + href);

    const appResponse = await page.goto(APP_URL.href, { waitUntil: 'domcontentloaded', timeout: 45000 });
    if (!appResponse || !appResponse.ok()) throw new Error('V386 app HTML did not return HTTP 200.');
    await page.waitForFunction(
      () => window.__lyLamAppBooted === true || window.__lyLamBootFailed === true,
      { timeout: 60000 },
    );
    const state = await page.evaluate(() => {
      const canvas = document.querySelector('#stage canvas');
      const controls = Array.from(document.querySelectorAll('#quick-controls button'));
      return {
        url: location.href,
        booted: window.__lyLamAppBooted === true,
        bootFailed: window.__lyLamBootFailed === true,
        rendererReady: window.__lyLamRendererReady === true,
        canvasCount: document.querySelectorAll('#stage canvas').length,
        status: document.querySelector('#status-message')?.textContent || '',
        controls: controls.map(button => ({
          id: button.id,
          visible: !!(button.offsetWidth && button.offsetHeight),
          minHeight: Math.round(button.getBoundingClientRect().height),
        })),
        webgl: !!canvas && typeof WebGLRenderingContext !== 'undefined',
      };
    });
    report.state = state;
    report.checks.appHttp200 = true;
    if (!state.booted || state.bootFailed) throw new Error('V386 avatar did not boot: ' + state.status);
    if (!state.rendererReady || state.canvasCount !== 1 || !state.webgl) throw new Error('WebGL renderer/canvas was not initialized.');
    if (state.controls.length !== 6 || state.controls.some(control => !control.visible || control.minHeight < 40)) {
      throw new Error('One or more mobile quick controls are missing or too small.');
    }
    if (!report.modelResponses.some(response => response.status === 200)) throw new Error('Candidate GLB did not return HTTP 200.');
    if (report.localThreeResponses.length !== 3 || report.localThreeResponses.some(response => response.status !== 200)) {
      throw new Error('Three.js core, GLTFLoader and OrbitControls did not all return HTTP 200.');
    }
    if (report.externalThreeRequests.length) throw new Error('Unexpected external Three.js CDN request.');
    if (report.pageErrors.length || report.consoleErrors.length || report.failedRequests.length) throw new Error('Browser page/console errors or failed requests detected.');

    await page.screenshot({ path: screenshotPath, fullPage: true });
    await page.locator('#view-face').click();
    await page.locator('#view-full').click();
    await page.locator('#zoom-in').click();
    await page.locator('#zoom-out').click();
    await page.locator('#view-reset').click();
    await page.locator('#help-toggle').click();
    if (!(await page.locator('#help').isVisible())) throw new Error('Mobile help panel did not open.');
    if (await page.locator('#help-toggle').getAttribute('aria-expanded') !== 'true') {
      throw new Error('Help button did not update aria-expanded=true.');
    }
    await page.locator('#help-toggle').click();
    if (await page.locator('#help').isVisible()) throw new Error('Mobile help panel did not close.');
    if (report.pageErrors.length || report.consoleErrors.length || report.failedRequests.length) throw new Error('Browser page/console errors occurred during mobile controls.');
    report.status = 'PASS_HTTPS_REVIEW_ROUTE';
    report.checks = { ...report.checks, localThreeModules200: true, candidateGlb200: true, mobileControls: 'PASS', helpToggle: 'PASS', noExternalCDN: true, noPageErrors: true, noConsoleErrors: true, noFailedRequests: true };
  } catch (error) {
    report.error = error && error.stack ? error.stack : String(error);
    console.error(report.error);
  } finally {
    fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
    if (browser) await browser.close().catch(() => {});
    console.log('V386_HTTPS_REVIEW_REPORT=' + JSON.stringify(report));
    if (report.status !== 'PASS_HTTPS_REVIEW_ROUTE') process.exitCode = 1;
  }
})();
