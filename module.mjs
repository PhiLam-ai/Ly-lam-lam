
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import './avatar_expression_motion.js';
import './avatar_api_recovery.js';
import './avatar_expression_composer.js';
import './avatar_morph_transition.js';
import './avatar_mesh_inspector.js';
const stage=document.querySelector('#stage'), status=document.querySelector('#status');
const scene=new THREE.Scene(); scene.background=new THREE.Color(0x101827);
const camera=new THREE.PerspectiveCamera(32,innerWidth/innerHeight,.1,100); camera.position.set(0,1.45,3.2);
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false}); renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.setSize(innerWidth,innerHeight); renderer.outputColorSpace=THREE.SRGBColorSpace; stage.appendChild(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xdce8ff,0x252c3a,2.0)); const key=new THREE.DirectionalLight(0xffe5cf,2.2); key.position.set(2,4,3);scene.add(key);
const controls=new OrbitControls(camera,renderer.domElement); controls.target.set(0,1.25,0); controls.enableDamping=true; controls.minDistance=1.8;controls.maxDistance=5;
let bindings=new Map(), targets={}, last=performance.now(), targetUrl='./lam-default.glb';
const morphTransition=globalThis.AvatarMorphTransition.createMorphTransition({timeConstantSeconds:.12});
let pollTimer=null, pollInFlight=false, viewerReady=false, disposed=false, debugWeights=null, apiFailureCount=0;
const retryPolicy=globalThis.AvatarApiRecovery.createRetryPolicy({baseDelayMs:1200,maxDelayMs:12000,factor:2});
const blinkController=globalThis.AvatarExpressionMotion.createBlinkController();
const diagnosticsEnabled=true;
const diagnostics=document.querySelector('#diagnostics'), morphButtons=document.querySelector('#morph-buttons'), diagResult=document.querySelector('#diag-result'), meshButtons=document.querySelector('#mesh-buttons');
let avatarScene=null, meshEntries=[], cameraDistance=3, vertexHighlightRecords=[], loadedVertexManifest=null, animationMixer=null, loadedAnimations=[];
if(diagnosticsEnabled) diagnostics.style.display='block';
const expectedMorphs=['smile','blink_left','blink_right','mouth_open','jaw_open','jaw_hinge','brow_raise','cheek_raise','lip_press','lip_fv','lip_round','tongue_tip'];
function clamp(v){v=Number(v);return Number.isFinite(v)?Math.max(0,Math.min(1,v)):0}
function collect(root){const m=new Map();root.traverse(n=>{if(!n.morphTargetDictionary||!n.morphTargetInfluences)return;for(const [name,raw] of Object.entries(n.morphTargetDictionary)){const i=Number(raw);if(Number.isInteger(i)&&i>=0&&i<n.morphTargetInfluences.length){if(!m.has(name))m.set(name,[]);m.get(name).push({node:n,index:i})}}});return m}
function apply(weights){for(const [name,list] of bindings){const goal=clamp(weights?.[name]);for(const {node,index} of list)node.morphTargetInfluences[index]=goal;}}
async function getState(){
  // Standalone preview: no backend/API dependency. Use the local diagnostic controls.
  targets={};
  status.textContent=`Bản xem thử cục bộ · ${bindings.size} morph · API chưa kết nối`;
}

if(diagnosticsEnabled){
  const presets={smile:{smile:.82,cheek_raise:.25},blink:{blink_left:1,blink_right:1},talk:{mouth_open:.62,jaw_open:.5,jaw_hinge:.35},fv:{lip_fv:.9,lip_press:.12},round:{lip_round:.9,mouth_open:.12}};
  document.querySelectorAll('[data-preset]').forEach(button=>button.addEventListener('click',()=>{const preset=presets[button.dataset.preset]||{};debugWeights=Object.fromEntries(expectedMorphs.map(key=>[key,preset[key]||0]));const active=Object.keys(preset).filter(key=>bindings.has(key));diagResult.textContent=`Tổ hợp ${button.textContent}: ${active.length}/${Object.keys(preset).length} morph có liên kết. Trọng số thử chỉ dùng cục bộ, không gửi lên API.`;}));
  for(const name of expectedMorphs){const button=document.createElement('button');button.type='button';button.textContent=name;button.dataset.morph=name;button.addEventListener('click',()=>{debugWeights=Object.fromEntries(expectedMorphs.map(key=>[key,key===name?0.85:0]));diagResult.textContent=bindings.has(name)?`Đang thử ${name}; có ${bindings.get(name).length} mesh liên kết.`:`Không tìm thấy morph ${name} trong mô hình.`;});morphButtons.appendChild(button);}
  document.querySelector('#api-mode').addEventListener('click',()=>{debugWeights=null;diagResult.textContent='Đã trở về trọng số do API cung cấp.';});
  document.querySelector('#neutral-mode').addEventListener('click',()=>{debugWeights=Object.fromEntries(expectedMorphs.map(name=>[name,0]));diagResult.textContent='Đang đưa tất cả morph về trung tính.';});
  const traceAnimation=document.querySelector('#trace-animation'), traceTime=document.querySelector('#trace-time'), traceTimeLabel=document.querySelector('#trace-time-label'), applyTimeTrace=document.querySelector('#apply-time-trace');
  function refreshTimeTrace(){if(!loadedVertexManifest||!loadedGltf)return;const selected=traceAnimation.value;const time=Number(traceTime.value);let playbackMessage='';if(selected){const seek=globalThis.AvatarMeshInspector.resolveAnimationSeek(loadedAnimations,selected,time);if(!seek.ok){diagResult.textContent=`Không thể phát animation: ${seek.reason}`;return;}if(animationMixer){animationMixer.stopAllAction();animationMixer.setTime(0);const action=animationMixer.clipAction(seek.clip);action.reset();action.play();animationMixer.setTime(seek.time);playbackMessage=` · GLTF ${seek.clip.name} @ ${seek.time.toFixed(2)}/${seek.duration.toFixed(2)} giây`;}}else if(animationMixer){animationMixer.stopAllAction();animationMixer.setTime(0);}const filtered=globalThis.AvatarMeshInspector.filterManifestAtTime(loadedVertexManifest,selected,time);globalThis.AvatarMeshInspector.clearVertexHighlights(vertexHighlightRecords);const result=globalThis.AvatarMeshInspector.applyVertexHighlights(THREE,loadedGltf,filtered.manifest);vertexHighlightRecords=result.records;diagResult.textContent=result.error?`Lỗi tô sáng: ${result.error}`:`Tại ${time.toFixed(2)} giây · ${selected||'mọi animation (chỉ lọc dấu vết)'}: ${result.matchedVertices} vertex tô sáng, ${result.unmatchedGroups} nhóm không khớp, ${filtered.matchedIntervals} khoảng thời gian phù hợp${playbackMessage}.`;}
  function updateTraceDuration(){const seek=globalThis.AvatarMeshInspector.resolveAnimationSeek(loadedAnimations,traceAnimation.value,Number(traceTime.value));if(seek.ok){traceTime.min='0';traceTime.max=String(Math.max(seek.duration,0.01));traceTime.value=String(Math.min(Number(traceTime.value),seek.duration));}else{const intervals=(loadedVertexManifest?.vertices||[]).flatMap(v=>v.flagged_intervals||[]).filter(i=>!traceAnimation.value||i.animation===traceAnimation.value);traceTime.min='0';traceTime.max=String(Math.max(0.01,...intervals.map(i=>Number(i.time_end)||0)));traceTime.value=String(Math.min(Number(traceTime.value),Number(traceTime.max)));}traceTimeLabel.value=Number(traceTime.value).toFixed(2);}
  document.querySelector('#vertex-manifest').addEventListener('change',async event=>{const file=event.target.files&&event.target.files[0];if(!file||!avatarScene)return;try{const manifest=JSON.parse(await file.text());const compatibility=globalThis.AvatarMeshInspector.validateManifestCompatibility(manifest,targetUrl,loadedAnimations);if(!compatibility.ok)throw new Error(`Manifest không tương thích (${compatibility.reason})${compatibility.missingAnimations?.length?`: thiếu animation: ${compatibility.missingAnimations.join(', ')}`:''}. Hãy dùng manifest được tạo từ đúng GLB.`);loadedVertexManifest=manifest;const flaggedNames=new Set(manifest.vertices.flatMap(v=>(v.flagged_intervals||[]).map(i=>i.animation)).filter(Boolean));traceAnimation.replaceChildren(new Option('Tất cả animation (chỉ lọc dấu vết)',''));for(const clip of loadedAnimations){const option=new Option(clip.name,clip.name);option.textContent=flaggedNames.has(clip.name)?`${clip.name} · có cảnh báo`:`${clip.name} · chưa có cảnh báo`;traceAnimation.add(option);}traceAnimation.disabled=traceTime.disabled=applyTimeTrace.disabled=false;updateTraceDuration();refreshTimeTrace();}catch(error){loadedVertexManifest=null;diagResult.textContent=`Không đọc được manifest: ${error.message}`;}});
  traceAnimation.addEventListener('change',()=>{updateTraceDuration();refreshTimeTrace();});traceTime.addEventListener('input',()=>{traceTimeLabel.value=Number(traceTime.value).toFixed(2);});applyTimeTrace.addEventListener('click',refreshTimeTrace);
  document.querySelector('#clear-vertex-highlights').addEventListener('click',()=>{globalThis.AvatarMeshInspector.clearVertexHighlights(vertexHighlightRecords);vertexHighlightRecords=[];diagResult.textContent='Đã xóa tô sáng vertex; hình học gốc được khôi phục.';});
  document.querySelectorAll('[data-camera]').forEach(button=>button.addEventListener('click',()=>{const p=globalThis.AvatarMeshInspector.getCameraPreset(button.dataset.camera,cameraDistance,0);if(!p)return;camera.position.set(p.x,p.y,p.z);controls.target.set(0,0,0);controls.update();diagResult.textContent=`Đã chuyển camera theo trục ${button.dataset.camera}. Có thể cần xoay thủ công để xác nhận hướng mặt thực tế.`;}));
}
const loader=new GLTFLoader();let loadedGltf=null;
loader.load(targetUrl,gltf=>{
  loadedGltf=gltf;
  if(disposed) return;
  loadedAnimations=Array.isArray(gltf.animations)?gltf.animations:[];
  animationMixer=new THREE.AnimationMixer(gltf.scene);
  scene.add(gltf.scene);avatarScene=gltf.scene;
  const box=new THREE.Box3().setFromObject(gltf.scene), size=box.getSize(new THREE.Vector3()), center=box.getCenter(new THREE.Vector3());
  gltf.scene.position.sub(center);
  const largest=Math.max(size.x,size.y,size.z,0.5);cameraDistance=Math.max(largest*2.3,2.2);
  camera.position.set(0,Math.max(size.y*.15,.2),cameraDistance);
  controls.target.set(0,0,0);controls.update();
  bindings=collect(gltf.scene);viewerReady=true;
  if(diagnosticsEnabled){
    meshEntries=globalThis.AvatarMeshInspector.collectMeshEntries(avatarScene);meshButtons.replaceChildren();
    for(const [index,entry] of meshEntries.entries()){const label=document.createElement('label'),input=document.createElement('input'),caption=document.createElement('span');input.type='checkbox';input.checked=entry.visible;input.addEventListener('change',()=>{globalThis.AvatarMeshInspector.setMeshVisibility(entry.node,input.checked);diagResult.textContent=`${input.checked?'Đang hiện':'Đã ẩn'} mesh ${entry.name}. Đây chỉ là công cụ kiểm tra, không sửa file GLB.`;});caption.textContent=`${index+1}. ${entry.name}`;label.append(input,caption);meshButtons.appendChild(label);}
    const missing=expectedMorphs.filter(name=>!bindings.has(name));diagResult.textContent=`Đã tải mô hình: ${bindings.size} tên morph; ${missing.length} tên chuẩn còn thiếu${missing.length?': '+missing.join(', '):'.'} Có ${meshEntries.length} mesh để kiểm tra.`;}
  status.textContent=`Mô hình đã tải · ${bindings.size} morph · chế độ xem thử cục bộ`;
  getState();
},undefined,e=>{status.textContent='Không tải được mô hình 3D. Hãy mở qua máy chủ web HTTPS và kiểm tra tệp lam-default.glb.';console.error(e)});
function frame(now){if(disposed)return;requestAnimationFrame(frame);const dt=(now-last)/1000;last=now;const base=debugWeights===null?targets:debugWeights;const blink=blinkController.update(now, !document.hidden && debugWeights===null);// Centralized coordination replaces direct weights.blink_left / weights.blink_right writes and the legacy AvatarExpressionComposer.composeExpressionWeights(weights) call.
const composed=globalThis.AvatarExpressionComposer.composeAvatarFrame(base,blink);const transitioned=morphTransition.update(composed,dt);apply(transitioned);controls.update();renderer.render(scene,camera)}requestAnimationFrame(frame);
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)});
document.addEventListener('visibilitychange',()=>{if(document.hidden){blinkController.reset();targets={};apiFailureCount=0;morphTransition.reset();if(pollTimer){clearTimeout(pollTimer);pollTimer=null;}}else if(viewerReady&&!pollTimer){retryPolicy.reset();getState();}});
window.addEventListener('pagehide',()=>{disposed=true;if(pollTimer)clearTimeout(pollTimer);globalThis.AvatarMeshInspector.clearVertexHighlights(vertexHighlightRecords);if(animationMixer)animationMixer.stopAllAction();renderer.dispose();});
