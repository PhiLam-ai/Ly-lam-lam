/* Testable, frame-rate-independent smoothing for avatar morph weights. */
(function(root){'use strict';
  function finiteWeight(value){const n=typeof value==='number'?value:Number(value);return Number.isFinite(n)?Math.max(0,Math.min(1,n)):0;}
  function positive(value,fallback){const n=Number(value);return Number.isFinite(n)&&n>0?n:fallback;}
  function createMorphTransition(options={}){
    const tau=positive(options.timeConstantSeconds,.12);
    let current={};
    function update(targets,dt){
      const seconds=Number.isFinite(Number(dt))?Math.max(0,Math.min(Number(dt),.25)):0;
      const alpha=1-Math.exp(-seconds/tau);
      const source=targets&&typeof targets==='object'&&!Array.isArray(targets)?targets:{};
      const keys=new Set([...Object.keys(current),...Object.keys(source)]), next={};
      for(const key of keys){const from=finiteWeight(current[key]),to=finiteWeight(source[key]);const value=from+(to-from)*alpha;next[key]=Math.abs(value)<1e-7?0:value;}
      current=next;return {...current};
    }
    function reset(values={}){current={};if(values&&typeof values==='object'&&!Array.isArray(values))for(const [k,v] of Object.entries(values))current[k]=finiteWeight(v);return {...current};}
    function snapshot(){return {...current};}
    return {update,reset,snapshot,timeConstantSeconds:tau};
  }
  const api={createMorphTransition,finiteWeight};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.AvatarMorphTransition=api;
})(typeof globalThis!=='undefined'?globalThis:this);
