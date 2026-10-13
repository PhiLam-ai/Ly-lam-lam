#!/usr/bin/env node
'use strict';

// Real Chromium smoke test for the V312 viewer. Requires Playwright installed.
// Starts a local static server, checks model/renderer startup, and saves a screenshot.
const { spawn } = require('node:child_process');
const path = require('node:path');
const { setTimeout: delay } = require('node:timers/promises');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const port = Number(process.env.PORT || 4173);
const baseUrl = `http://127.0.0.1:${port}/`;
const screenshotPath = path.join(root, 'avatar-browser-smoke.png');
let server;
let browser;

async function waitForServer(url, timeoutMs = 15000) {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {}
    await delay(250);
  }
  throw new Error(`Static server did not become ready at ${url}`);
}

(async () => {
  const errors = [];
  const failedRequests = [];
  let glbStatus = null;

  try {
    server = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1', '--directory', root], {
      stdio: 'ignore'
    });
    await waitForServer(baseUrl);
    browser = await chromium.launch({
      headless: true,
      args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist']
    });
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') errors.push(message.text());
    });
    page.on('requestfailed', request => failedRequests.push({
      url: request.url(),
      error: request.failure()?.errorText || 'unknown'
    }));
    page.on('response', response => {
      if (response.url().endsWith('/lam-default.glb')) glbStatus = response.status();
    });

    const response = await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    if (!response || !response.ok()) throw new Error(`Viewer HTTP response was ${response?.status() ?? 'missing'}`);

    await page.waitForFunction(() =>
      window.__lyLamAppBooted === true ||
      window.__lyLamBootFailed === true,
      undefined,
      { timeout: 45000 }
    );
    await page.waitForTimeout(1000);

    const state = await page.evaluate(() => ({
      title: document.title,
      booted: window.__lyLamAppBooted === true,
      rendererReady: window.__lyLamRendererReady === true,
      bootFailure: window.__lyLamBootFailed || null,
      canvasCount: document.querySelectorAll('canvas').length,
      statusText: document.querySelector('#status-message')?.textContent?.trim() || '',
      stageSize: (() => {
        const rect = document.querySelector('#stage')?.getBoundingClientRect();
        return rect ? { width: Math.round(rect.width), height: Math.round(rect.height) } : null;
      })()
    }));
    await page.screenshot({ path: screenshotPath, fullPage: true });

    console.log(JSON.stringify({ state, glbStatus, errors, failedRequests, screenshotPath }, null, 2));

    if (!state.booted) throw new Error(`Model did not finish loading: ${state.bootFailure || state.statusText}`);
    if (!state.rendererReady) throw new Error('Renderer-ready flag was not set');
    if (state.canvasCount < 1) throw new Error('No WebGL canvas was created');
    if (glbStatus !== 200) throw new Error(`GLB request status expected 200, got ${glbStatus}`);
    if (errors.length) throw new Error(`Browser reported console/page errors: ${errors.join(' | ')}`);
    if (failedRequests.some(item => item.url.includes('three.module.js') || item.url.includes('GLTFLoader.js'))) {
      throw new Error('A required Three.js module request failed');
    }
    console.log('PASS: Chromium loaded the GLB and initialized the viewer.');
  } catch (error) {
    console.error('FAIL:', error.stack || error.message || String(error));
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close().catch(() => {});
    if (server) server.kill('SIGTERM');
  }
})();
