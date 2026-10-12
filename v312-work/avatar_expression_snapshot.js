/* Portable, validated snapshots for local avatar morph experiments. */
(function(root){'use strict';
  const SCHEMA='ly-lam-lam-expression-snapshot';
  function clamp(value){const n=typeof value==='number'?value:Number(value);return Number.isFinite(n)?Math.max(0,Math.min(1,n)):0;}
  function createSnapshot(weights, expectedMorphs, asset='./lam-default.glb'){
    if(!Array.isArray(expectedMorphs)||!expectedMorphs.length)throw new TypeError('expectedMorphs must be a non-empty array');
    const morph_weights={};
    for(const name of expectedMorphs){if(typeof name!=='string'||!name)continue;morph_weights[name]=clamp(weights&&Object.prototype.hasOwnProperty.call(weights,name)?weights[name]:0);}
    return {schema:SCHEMA,version:1,asset,morph_weights};
  }
  function parseSnapshot(input, expectedMorphs, asset='./lam-default.glb'){
    let data=input;
    try{if(typeof input==='string')data=JSON.parse(input);}catch(_){return {ok:false,reason:'invalid-json'};}
    if(!data||typeof data!=='object'||Array.isArray(data)||data.schema!==SCHEMA||data.version!==1||typeof data.morph_weights!=='object'||!data.morph_weights||Array.isArray(data.morph_weights))return {ok:false,reason:'invalid-schema'};
    if(data.asset!==asset)return {ok:false,reason:'asset-mismatch'};
    const allowed=new Set(expectedMorphs);const unknown=Object.keys(data.morph_weights).filter(key=>!allowed.has(key));
    if(unknown.length)return {ok:false,reason:'unknown-morphs',unknown};
    const weights={};for(const name of expectedMorphs){const value=data.morph_weights[name];if(value===undefined){weights[name]=0;continue;}const n=typeof value==='number'?value:Number(value);if(!Number.isFinite(n))return {ok:false,reason:'invalid-weight',morph:name};weights[name]=clamp(n);}
    return {ok:true,weights};
  }
  const api={createSnapshot,parseSnapshot,clamp,SCHEMA};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.AvatarExpressionSnapshot=api;
})(typeof globalThis!=='undefined'?globalThis:this);
