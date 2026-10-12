#!/usr/bin/env node
'use strict';
// One-command, fail-fast launch-readiness gate for the V312 package.
// This validates source assets and a local HTTP simulation; it does not claim browser rendering.
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const steps = [
  ['Startup preflight', ['tools/startup-preflight.cjs']],
  ['Three.js module integrity', ['tools/vendor-module-integrity.cjs', root]],
  ['Regression tests', ['--test', 'tests/*.test.cjs']],
  ['Static HTTP smoke', ['tools/static-http-smoke.cjs']],
  ['Real preview-server integration', ['tools/preview-server-integration.cjs']]
];
for (const [label, args] of steps) {
  console.log(`\n=== ${label} ===`);
  let result;
  if (args[0] === '--test') {
    // Avoid shell glob differences between Windows PowerShell and POSIX shells.
    const fs = require('node:fs');
    const testDir = path.join(root, 'tests');
    const files = fs.readdirSync(testDir).filter(name => name.endsWith('.test.cjs')).sort().map(name => path.join(testDir, name));
    result = spawnSync(process.execPath, ['--test', ...files], { cwd: root, encoding: 'utf8', windowsHide: true });
  } else {
    result = spawnSync(process.execPath, args, { cwd: root, encoding: 'utf8', windowsHide: true });
  }
  if (result.error) {
    console.error(`FAIL: không chạy được bước “${label}”: ${result.error.message}`);
    process.exit(1);
  }
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.status !== 0) {
    console.error(`FAIL: bước “${label}” kết thúc với mã ${result.status}`);
    process.exit(result.status || 1);
  }
  console.log(`PASS: ${label}`);
}
console.log('\nPASS V312 STARTUP GATE: các kiểm tra tự động đều đạt.');
console.log('GIỚI HẠN: chưa xác minh WebGL/GPU, render avatar trên trình duyệt thật, HTTPS hosting hoặc Safari/iPhone.');
