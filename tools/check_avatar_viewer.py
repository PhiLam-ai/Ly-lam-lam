#!/usr/bin/env python3
"""Fast, dependency-free checks for the web avatar viewer."""
from pathlib import Path
import json
import re
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
errors = []
checks = 0

def check(condition, message):
    global checks
    checks += 1
    if condition:
        print(f"PASS: {message}")
    else:
        errors.append(message)
        print(f"FAIL: {message}")

html_path = ROOT / "index.html"
check(html_path.is_file(), "index.html exists")
html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
check('<div id="stage"></div>' in html, "3D stage exists")
check("new GLTFLoader" in html and "loader.load(targetUrl" in html, "GLTFLoader is wired to load the avatar")
check("new THREE.WebGLRenderer" in html, "WebGL renderer is initialized")
check("setTimeout" in html and "15 giây" in html, "slow-load diagnostic is present")
check("new URL('./lam-default.glb',location.href)" in html, "GLB path resolves relative to the app URL")

for match in re.findall(r"""import\s+['"]\./([^'"]+)['"]\s*;""", html):
    check((ROOT / match).is_file(), f"viewer module exists: {match}")

inline_scripts = re.findall(r'<script type="module">(.*?)</script>', html, re.S)
check(bool(inline_scripts), "inline ES module exists")
if inline_scripts:
    with tempfile.TemporaryDirectory() as td:
        js = Path(td) / "viewer-check.mjs"
        js.write_text(inline_scripts[0], encoding="utf-8")
        result = subprocess.run(["node", "--check", str(js)], text=True, capture_output=True)
        check(result.returncode == 0, "inline viewer JavaScript syntax passes node --check")
        if result.returncode:
            print(result.stderr)

glb_path = ROOT / "lam-default.glb"
check(glb_path.is_file(), "lam-default.glb exists")
if glb_path.is_file():
    data = glb_path.read_bytes()
    check(len(data) >= 20, "GLB has a minimally valid header")
    if len(data) >= 20:
        magic, version, declared_length, chunk_length, chunk_type = struct.unpack_from("<4sIIII", data, 0)
        check(magic == b"glTF" and version == 2, "GLB magic and version are valid")
        check(declared_length == len(data), "GLB declared length matches file size")
        check(chunk_type == 0x4E4F534A and 20 + chunk_length <= len(data), "GLB JSON chunk header is valid")
        if magic == b"glTF" and version == 2 and chunk_type == 0x4E4F534A and 20 + chunk_length <= len(data):
            try:
                doc = json.loads(data[20:20 + chunk_length].decode("utf-8").rstrip(" \\t\\r\\n\\0"))
                check(isinstance(doc.get("nodes"), list) and len(doc["nodes"]) > 0, "GLB contains scene nodes")
                check(isinstance(doc.get("meshes"), list) and len(doc["meshes"]) > 0, "GLB contains meshes")
            except Exception as exc:
                check(False, f"GLB JSON parses: {exc}")

print(f"\nRESULT: {checks - len(errors)}/{checks} checks passed")
if errors:
    raise SystemExit(1)
