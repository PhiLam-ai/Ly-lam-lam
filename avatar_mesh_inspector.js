/* Opt-in, testable helpers for inspecting GLTF mesh visibility and camera presets. */
(function(root){'use strict';
  function collectMeshEntries(scene){
    const entries=[]; if(!scene||typeof scene.traverse!=='function') return entries;
    scene.traverse(node=>{if(node&&node.isMesh) entries.push({node,name:String(node.name||`mesh-${entries.length+1}`),visible:node.visible!==false});});
    return entries;
  }
  function setMeshVisibility(node,visible){if(!node||typeof node!=='object') return false;node.visible=Boolean(visible);return node.visible;}
  function getCameraPreset(name,distance,centerY=0){
    const d=Number.isFinite(Number(distance))?Math.max(0.1,Number(distance)):3;
    const y=Number.isFinite(Number(centerY))?Number(centerY):0;
    const positions={front:{x:0,y,z:d},back:{x:0,y,z:-d},left:{x:-d,y,z:0},right:{x:d,y,z:0}};
    const p=positions[name];return p?{...p}:null;
  }
  function buildVertexHighlightGroups(manifest){
    if(!manifest||manifest.manifest!=='V206 vertex inspection manifest'||!Array.isArray(manifest.vertices)) return [];
    const groups=new Map();
    for(const row of manifest.vertices){
      if(!row||typeof row.vertex_id!=='string') continue;
      const keys=['node_index','mesh_index','primitive_index','vertex_index'];
      if(!keys.every(k=>Number.isInteger(row[k])&&row[k]>=0)) continue;
      const key=`${row.node_index}/${row.mesh_index}/${row.primitive_index}`;
      if(!groups.has(key)) groups.set(key,{nodeIndex:row.node_index,meshIndex:row.mesh_index,primitiveIndex:row.primitive_index,vertexIndices:[],vertices:[]});
      const group=groups.get(key); group.vertexIndices.push(row.vertex_index);
      group.vertices.push({vertexId:row.vertex_id,vertexIndex:row.vertex_index,peakVelocity:Number.isFinite(row.peak_velocity_magnitude_per_second)?row.peak_velocity_magnitude_per_second:null,flaggedTransitionCount:Number.isInteger(row.flagged_transition_count)?row.flagged_transition_count:0});
    }
    return Array.from(groups.values()).map(g=>({...g,vertexIndices:Array.from(new Set(g.vertexIndices)).sort((a,b)=>a-b)})).sort((a,b)=>a.nodeIndex-b.nodeIndex||a.meshIndex-b.meshIndex||a.primitiveIndex-b.primitiveIndex);
  }
  function validateManifestCompatibility(manifest,assetUrl,animations){
    if(!manifest||manifest.manifest!=='V206 vertex inspection manifest'||!Array.isArray(manifest.vertices)) return {ok:false,reason:'invalid-manifest'};
    const basename=value=>String(value||'').split(/[?#]/,1)[0].split('/').filter(Boolean).pop()||'';
    const expected=basename(manifest.asset), actual=basename(assetUrl);
    if(!expected||!actual) return {ok:false,reason:'missing-asset-identity',expected,actual};
    if(expected!==actual) return {ok:false,reason:'asset-name-mismatch',expected,actual};
    const expectedNames=Array.isArray(manifest.animation_names)?manifest.animation_names.filter(n=>typeof n==='string').slice().sort():[];
    const actualNames=Array.isArray(animations)?animations.map(a=>a&&a.name).filter(n=>typeof n==='string').sort():[];
    const missing=expectedNames.filter(n=>!actualNames.includes(n));
    if(missing.length) return {ok:false,reason:'animation-name-mismatch',expected,actual,missingAnimations:missing};
    return {ok:true,reason:null,expected,actual,checkedAnimationNames:expectedNames.length};
  }
  function resolveAnimationSeek(animations,animationName,timeSeconds){
    if(!Array.isArray(animations)) return {ok:false,reason:'missing-animations'};
    const clip=animations.find(item=>item&&typeof item.name==='string'&&item.name===animationName);
    if(!clip) return {ok:false,reason:'animation-not-found'};
    const duration=Number(clip.duration), requested=Number(timeSeconds);
    if(!Number.isFinite(duration)||duration<0||!Number.isFinite(requested)) return {ok:false,reason:'invalid-time-or-duration'};
    return {ok:true,clip,duration,time:Math.min(duration,Math.max(0,requested))};
  }
  function filterManifestAtTime(manifest,animationName,timeSeconds){
    if(!manifest||manifest.manifest!=='V206 vertex inspection manifest'||!Array.isArray(manifest.vertices)||!Number.isFinite(Number(timeSeconds))) return {manifest:{manifest:'V206 vertex inspection manifest',schema_version:1,asset:manifest&&manifest.asset,thresholds:manifest&&manifest.thresholds,summary:{unique_flagged_vertices:0},vertices:[]},matchedIntervals:0,invalidManifest:true};
    const t=Number(timeSeconds), vertices=[]; let matchedIntervals=0;
    for(const row of manifest.vertices){
      if(!row||!Array.isArray(row.flagged_intervals)) continue;
      const intervals=row.flagged_intervals.filter(interval=>interval&&typeof interval.animation==='string'&&(!animationName||interval.animation===animationName)&&Number.isFinite(interval.time_start)&&Number.isFinite(interval.time_end)&&t>=interval.time_start-1e-9&&t<=interval.time_end+1e-9);
      if(!intervals.length) continue;
      matchedIntervals+=intervals.length;
      vertices.push({...row,flagged_intervals:intervals,animations:[...new Set(intervals.map(i=>i.animation))]});
    }
    return {manifest:{...manifest,vertices,summary:{...(manifest.summary||{}),unique_flagged_vertices:vertices.length}},matchedIntervals,invalidManifest:false};
  }
  function clearVertexHighlights(records){
    if(!Array.isArray(records)) return 0;
    for(const record of records){
      if(!record||!record.mesh) continue;
      record.mesh.geometry=record.originalGeometry;
      record.mesh.material=record.originalMaterial;
      if(record.highlightGeometry&&typeof record.highlightGeometry.dispose==='function') record.highlightGeometry.dispose();
      if(Array.isArray(record.highlightMaterial)) record.highlightMaterial.forEach(m=>m&&m.dispose&&m.dispose());
      else if(record.highlightMaterial&&record.highlightMaterial.dispose) record.highlightMaterial.dispose();
    }
    return records.length;
  }
  function applyVertexHighlights(THREE,gltf,manifest){
    if(!THREE||!gltf||!gltf.scene||!gltf.parser||!gltf.parser.associations) return {records:[],matchedVertices:0,unmatchedGroups:0,error:'missing-gltf-associations'};
    const groups=buildVertexHighlightGroups(manifest), associationMap=gltf.parser.associations, records=[];
    const wanted=new Map(groups.map(g=>[`${g.nodeIndex}/${g.meshIndex}/${g.primitiveIndex}`,g]));
    let matchedVertices=0, unmatchedGroups=0;
    gltf.scene.traverse(mesh=>{
      if(!mesh||!mesh.isMesh||!mesh.geometry) return;
      const association=associationMap.get(mesh);
      if(!association||!Number.isInteger(association.nodes)||!Number.isInteger(association.meshes)) return;
      const primitive=Number.isInteger(association.primitives)?association.primitives:0;
      const key=`${association.nodes}/${association.meshes}/${primitive}`, group=wanted.get(key);
      if(!group) return;
      const originalGeometry=mesh.geometry, originalMaterial=mesh.material;
      const geometry=originalGeometry.clone(), position=geometry.getAttribute('position');
      if(!position){geometry.dispose();unmatchedGroups++;return;}
      const colors=new Float32Array(position.count*3);
      for(let i=0;i<position.count;i++){colors[i*3]=1;colors[i*3+1]=1;colors[i*3+2]=1;}
      let applied=0;
      for(const index of group.vertexIndices){if(index<0||index>=position.count) continue;colors[index*3]=1;colors[index*3+1]=0.16;colors[index*3+2]=0.035;applied++;}
      if(!applied){geometry.dispose();unmatchedGroups++;return;}
      geometry.setAttribute('color',new THREE.BufferAttribute(colors,3));
      const sourceMaterials=Array.isArray(originalMaterial)?originalMaterial:[originalMaterial];
      const highlightMaterials=sourceMaterials.map(material=>{const clone=material.clone();clone.vertexColors=true;clone.needsUpdate=true;return clone;});
      mesh.geometry=geometry;mesh.material=Array.isArray(originalMaterial)?highlightMaterials:highlightMaterials[0];
      records.push({mesh,originalGeometry,originalMaterial,highlightGeometry:geometry,highlightMaterial:Array.isArray(mesh.material)?mesh.material:[mesh.material]});
      matchedVertices+=applied;wanted.delete(key);
    });
    unmatchedGroups+=wanted.size;
    return {records,matchedVertices,unmatchedGroups,error:null};
  }
  const api={collectMeshEntries,setMeshVisibility,getCameraPreset,buildVertexHighlightGroups,filterManifestAtTime,validateManifestCompatibility,resolveAnimationSeek,applyVertexHighlights,clearVertexHighlights};
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
  root.AvatarMeshInspector=api;
})(typeof globalThis!=='undefined'?globalThis:this);
