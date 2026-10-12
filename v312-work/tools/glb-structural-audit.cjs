'use strict';

function auditGlbBytes(input) {
  const errors = [];
  if (!Buffer.isBuffer(input)) input = Buffer.from(input || []);
  if (input.length < 20 || input.toString('ascii', 0, 4) !== 'glTF') {
    return { ok: false, errors: ['GLB thiếu header hoặc magic glTF không hợp lệ.'] };
  }
  const version = input.readUInt32LE(4);
  const declaredLength = input.readUInt32LE(8);
  if (version !== 2) errors.push(`GLB version phải là 2, nhận được ${version}.`);
  if (declaredLength !== input.length) errors.push(`Độ dài header ${declaredLength} không khớp tệp ${input.length}.`);

  const chunks = [];
  let offset = 12;
  while (offset < input.length) {
    if (offset + 8 > input.length) { errors.push('Header chunk bị cắt cụt.'); break; }
    const length = input.readUInt32LE(offset);
    const type = input.readUInt32LE(offset + 4);
    offset += 8;
    if (length % 4 !== 0) errors.push(`Chunk ${chunks.length} có độ dài không căn chỉnh 4 byte.`);
    if (offset + length > input.length) { errors.push(`Chunk ${chunks.length} vượt quá cuối tệp.`); break; }
    chunks.push({ type, data: input.subarray(offset, offset + length), length });
    offset += length;
  }
  if (offset !== input.length) errors.push('Các chunk không kết thúc đúng tại cuối tệp.');
  const JSON_CHUNK = 0x4e4f534a;
  const BIN_CHUNK = 0x004e4942;
  if (!chunks.length || chunks[0].type !== JSON_CHUNK) errors.push('Chunk đầu tiên phải là JSON.');
  const jsonChunks = chunks.filter(chunk => chunk.type === JSON_CHUNK);
  const binChunks = chunks.filter(chunk => chunk.type === BIN_CHUNK);
  if (jsonChunks.length !== 1) errors.push(`GLB phải có đúng một JSON chunk; nhận được ${jsonChunks.length}.`);
  if (binChunks.length > 1) errors.push(`GLB chỉ được có tối đa một BIN chunk; nhận được ${binChunks.length}.`);

  let doc = null;
  if (jsonChunks.length === 1) {
    try { doc = JSON.parse(jsonChunks[0].data.toString('utf8').replace(/[\u0000\u0020\t\r\n]+$/g, '')); }
    catch (error) { errors.push(`JSON chunk không hợp lệ: ${error.message}`); }
  }
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) {
    if (doc !== null) errors.push('JSON chunk phải là một object glTF.');
    return { ok: errors.length === 0, errors, summary: null };
  }
  if (doc.asset?.version !== '2.0') errors.push(`asset.version phải là "2.0", nhận được ${String(doc.asset?.version)}.`);

  const buffers = Array.isArray(doc.buffers) ? doc.buffers : [];
  const views = Array.isArray(doc.bufferViews) ? doc.bufferViews : [];
  const accessors = Array.isArray(doc.accessors) ? doc.accessors : [];
  const binLength = binChunks[0]?.length || 0;
  if (buffers.length > 1) errors.push('GLB chuẩn chỉ hỗ trợ một buffer nhúng trong tệp này.');
  for (let i = 0; i < buffers.length; i++) {
    const buffer = buffers[i];
    if (!Number.isSafeInteger(buffer.byteLength) || buffer.byteLength < 0) errors.push(`buffers[${i}].byteLength không hợp lệ.`);
    if (buffer.uri !== undefined) errors.push(`buffers[${i}] có URI ngoài; gói xem thử yêu cầu dữ liệu nhúng trong GLB.`);
    if (i === 0 && buffer.byteLength > binLength) errors.push(`Buffer khai báo ${buffer.byteLength} byte nhưng BIN chunk chỉ có ${binLength} byte.`);
    if (i === 0 && buffer.byteLength > 0 && !binChunks.length) errors.push('Thiếu BIN chunk cho buffer nhúng.');
  }
  for (let i = 0; i < views.length; i++) {
    const view = views[i];
    const bufferIndex = view.buffer ?? 0;
    const start = view.byteOffset ?? 0;
    const length = view.byteLength;
    if (!Number.isInteger(bufferIndex) || bufferIndex < 0 || bufferIndex >= buffers.length) { errors.push(`bufferViews[${i}].buffer trỏ tới buffer không tồn tại.`); continue; }
    if (!Number.isSafeInteger(start) || start < 0 || !Number.isSafeInteger(length) || length < 0) { errors.push(`bufferViews[${i}] có byteOffset/byteLength không hợp lệ.`); continue; }
    if (start + length > buffers[bufferIndex].byteLength) errors.push(`bufferViews[${i}] vượt quá độ dài buffer khai báo.`);
    if (bufferIndex === 0 && start + length > binLength) errors.push(`bufferViews[${i}] vượt quá dữ liệu BIN thực tế.`);
  }
  for (let i = 0; i < accessors.length; i++) {
    const accessor = accessors[i];
    if (!Number.isSafeInteger(accessor.count) || accessor.count < 0) errors.push(`accessors[${i}].count không hợp lệ.`);
    if (accessor.bufferView !== undefined && (!Number.isInteger(accessor.bufferView) || accessor.bufferView < 0 || accessor.bufferView >= views.length)) errors.push(`accessors[${i}].bufferView trỏ tới bufferView không tồn tại.`);
    if (accessor.sparse) {
      const sparse = accessor.sparse;
      if (!Number.isSafeInteger(sparse.count) || sparse.count < 0 || sparse.count > accessor.count) errors.push(`accessors[${i}].sparse.count không hợp lệ.`);
      for (const [label, ref] of [['indices', sparse.indices], ['values', sparse.values]]) {
        if (!ref || !Number.isInteger(ref.bufferView) || ref.bufferView < 0 || ref.bufferView >= views.length) errors.push(`accessors[${i}].sparse.${label} trỏ tới bufferView không tồn tại.`);
      }
    }
  }
  for (const [kind, entries] of [['images', doc.images], ['meshes', doc.meshes], ['nodes', doc.nodes], ['skins', doc.skins], ['scenes', doc.scenes]]) {
    if (!Array.isArray(entries)) continue;
    for (let i = 0; i < entries.length; i++) {
      const entry = entries[i];
      const refs = [];
      if (kind === 'images' && entry.bufferView !== undefined) refs.push(['bufferView', entry.bufferView, views.length]);
      if (kind === 'meshes') for (const [name, primitive] of (entry.primitives || []).entries()) {
        if (primitive.indices !== undefined) refs.push([`primitive ${name} indices accessor`, primitive.indices, accessors.length]);
        for (const accessor of Object.values(primitive.attributes || {})) refs.push([`primitive ${name} attribute accessor`, accessor, accessors.length]);
        for (const target of primitive.targets || []) for (const accessor of Object.values(target)) refs.push([`primitive ${name} morph accessor`, accessor, accessors.length]);
      }
      if (kind === 'nodes') {
        if (entry.mesh !== undefined) refs.push(['mesh', entry.mesh, (doc.meshes || []).length]);
        if (entry.skin !== undefined) refs.push(['skin', entry.skin, (doc.skins || []).length]);
        for (const child of entry.children || []) refs.push(['child node', child, (doc.nodes || []).length]);
      }
      if (kind === 'skins') for (const joint of entry.joints || []) refs.push(['joint node', joint, (doc.nodes || []).length]);
      if (kind === 'scenes') for (const node of entry.nodes || []) refs.push(['scene node', node, (doc.nodes || []).length]);
      for (const [label, ref, count] of refs) if (!Number.isInteger(ref) || ref < 0 || ref >= count) errors.push(`${kind}[${i}] ${label} trỏ tới phần tử không tồn tại.`);
    }
  }
  return {
    ok: errors.length === 0,
    errors,
    summary: {
      bytes: input.length,
      jsonBytes: jsonChunks[0]?.length || 0,
      binaryBytes: binLength,
      nodes: Array.isArray(doc.nodes) ? doc.nodes.length : 0,
      meshes: Array.isArray(doc.meshes) ? doc.meshes.length : 0,
      accessors: accessors.length,
      bufferViews: views.length,
      animations: Array.isArray(doc.animations) ? doc.animations.length : 0
    }
  };
}

module.exports = { auditGlbBytes };
