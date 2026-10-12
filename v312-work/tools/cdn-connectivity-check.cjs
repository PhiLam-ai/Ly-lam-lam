#!/usr/bin/env node
'use strict';
const https = require('node:https');
const urls = [
  ['Three.js core', 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js'],
  ['GLTFLoader addon', 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/loaders/GLTFLoader.js'],
  ['OrbitControls addon', 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js'],
  ['Alternate CDN Three.js core (unpkg)', 'https://unpkg.com/three@0.160.0/build/three.module.js']
];
const timeoutMs = Number(process.env.CDN_CHECK_TIMEOUT_MS || 7000);
function probe(label, url) {
  return new Promise(resolve => {
    const req = https.get(url, { timeout: timeoutMs, headers: { 'user-agent': 'LiyLamLam-CDN-Preflight/1.0' } }, res => {
      res.resume();
      const ok = res.statusCode >= 200 && res.statusCode < 300;
      console.log(`${ok ? 'PASS' : 'FAIL'} ${label}: HTTP ${res.statusCode}`);
      resolve(ok);
    });
    req.on('timeout', () => req.destroy(new Error(`timeout sau ${timeoutMs} ms`)));
    req.on('error', err => {
      console.log(`FAIL ${label}: ${err.code || err.message}`);
      resolve(false);
    });
  });
}
(async () => {
  console.log('Kiểm tra tùy chọn CDN Three.js; không tải hoặc lưu thư viện.');
  const results = await Promise.all(urls.map(([label, url]) => probe(label, url)));
  if (results.every(Boolean)) {
    console.log('CDN phản hồi được từ môi trường hiện tại. Điều này chưa xác nhận trình duyệt/iPhone sẽ truy cập được hoặc WebGL render thành công.');
  } else {
    console.log('Ít nhất một URL CDN không truy cập được từ môi trường hiện tại. Kiểm tra DNS, Internet, proxy hoặc thử từ chính thiết bị triển khai.');
    process.exitCode = 1;
  }
})().catch(err => { console.error(err.message); process.exitCode = 1; });
