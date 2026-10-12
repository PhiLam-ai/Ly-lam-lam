#!/usr/bin/env node
'use strict';
// Assemble a minimal, self-contained Pages artifact without publishing test harnesses,
// package-acquisition tools, or project audit documents as public static assets.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const output = path.resolve(process.argv[2] || path.join(root, 'dist'));
const required = ['index.html', 'module.mjs', 'lam-default.glb', 'expression-baseline-cases-v1.json', '.nojekyll'];
function fail(message) { console.error(`FAIL: ${message}`); process.exit(1); }
if (output === root || root.startsWith(output + path.sep)) fail('đích artifact không được là thư mục gốc dự án hoặc thư mục cha của dự án');
for (const file of required) {
  const full = path.join(root, file);
  let info;
  try { info = fs.lstatSync(full); } catch { fail(`thiếu tài nguyên triển khai ${file}`); }
  if (info.isSymbolicLink() || !info.isFile()) fail(`tài nguyên triển khai phải là tệp thường, không phải symbolic link: ${file}`);
}
// Assemble in a sibling temporary directory, then replace the destination only after validation.
const parent = path.dirname(output);
const temp = path.join(parent, `.${path.basename(output)}-staging-${process.pid}`);
try {
  fs.mkdirSync(parent, { recursive: true });
  fs.rmSync(temp, { recursive: true, force: true });
  fs.mkdirSync(temp, { recursive: true });
  const copyFile = relative => {
    const from = path.join(root, relative), to = path.join(temp, relative);
    let info;
    try { info = fs.lstatSync(from); } catch { throw new Error(`thiếu tệp được tham chiếu: ${relative}`); }
    if (info.isSymbolicLink() || !info.isFile()) throw new Error(`tệp được tham chiếu phải là tệp thường, không phải symbolic link: ${relative}`);
    fs.mkdirSync(path.dirname(to), { recursive: true });
    fs.copyFileSync(from, to);
  };
  for (const file of required) copyFile(file);
  // Include all root JS modules because the preview loads diagnostic/expression modules lazily.
  for (const name of fs.readdirSync(root)) {
    if (!/\.(?:js|mjs)$/.test(name)) continue;
    const info = fs.lstatSync(path.join(root, name));
    if (info.isSymbolicLink()) throw new Error(`không chấp nhận symbolic link ở thư mục gốc: ${name}`);
    if (info.isFile()) copyFile(name);
  }
  const vendor = path.join(root, 'vendor', 'three');
  if (fs.existsSync(vendor)) fs.cpSync(vendor, path.join(temp, 'vendor', 'three'), { recursive: true });
  // Walk every shipped JS module recursively, including nested vendor/three modules.
  // Checking only root-level modules can miss broken imports inside a staged dependency.
  const walkFiles = directory => {
    const found = [];
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const absolute = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) throw new Error(`artifact không chấp nhận symbolic link: ${path.relative(temp, absolute)}`);
      if (entry.isDirectory()) found.push(...walkFiles(absolute));
      else if (entry.isFile()) found.push(path.relative(temp, absolute).split(path.sep).join('/'));
    }
    return found;
  };
  const shippedFiles = walkFiles(temp);
  const sources = ['index.html', ...shippedFiles.filter(name => /\.(?:js|mjs)$/.test(name))];
  const edges = new Set();
  for (const sourceName of sources) {
    const source = fs.readFileSync(path.join(temp, sourceName), 'utf8');
    for (const match of source.matchAll(/(?:\bfrom\s*|\bimport\s*(?:\(\s*)?)['"](\.{1,2}\/[^'"]+)['"]/g)) {
      const specifier = match[1];
      const localSpecifier = specifier.split(/[?#]/, 1)[0];
      const target = path.resolve(temp, path.dirname(sourceName), localSpecifier);
      if (!target.startsWith(temp + path.sep) || !fs.existsSync(target) || !fs.statSync(target).isFile()) throw new Error(`${sourceName}: import không có trong artifact: ${specifier}`);
      edges.add(`${sourceName} -> ${specifier}`);
    }
  }
  // Public artifact should not include build/test tooling or internal audit notes.
  for (const forbidden of ['tests', 'tools', 'README-VI.txt', 'TESTING-VI.txt', 'VERSION.txt', 'SHA256SUMS.txt']) {
    if (fs.existsSync(path.join(temp, forbidden))) throw new Error(`artifact chứa tài nguyên không nên công khai: ${forbidden}`);
  }
  const old = `${output}.previous-${process.pid}`;
  fs.rmSync(old, { recursive: true, force: true });
  const hadOutput = fs.existsSync(output);
  if (hadOutput) fs.renameSync(output, old);
  try { fs.renameSync(temp, output); }
  catch (error) {
    if (hadOutput && fs.existsSync(old)) fs.renameSync(old, output);
    throw error;
  }
  fs.rmSync(old, { recursive: true, force: true });
  const count = walkFiles(output).length;
  console.log(`PASS: artifact Pages tạo thành công: ${count} tệp; ${edges.size} cạnh import tương đối đã xác minh.`);
  console.log(`Đích artifact: ${output}`);
  console.log('Không đưa tests/, tools/ hoặc tài liệu kiểm thử vào artifact công khai.');
} catch (error) {
  fs.rmSync(temp, { recursive: true, force: true });
  console.error(`FAIL: không thể tạo artifact Pages: ${error.message}`);
  process.exit(1);
}
