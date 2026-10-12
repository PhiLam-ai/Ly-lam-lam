/* Quantitative comparison of two validated local expression snapshots. */
(function(root){'use strict';
  function compareSnapshots(inputA,inputB,expectedMorphs,asset='./lam-default.glb'){
    const snapshotApi=root.AvatarExpressionSnapshot || (typeof require==='function'?require('./avatar_expression_snapshot.js'):null);
    if(!snapshotApi)return {ok:false,reason:'snapshot-api-unavailable'};
    const a=snapshotApi.parseSnapshot(inputA,expectedMorphs,asset);
    if(!a.ok)return {ok:false,side:'A',reason:a.reason,details:a};
    const b=snapshotApi.parseSnapshot(inputB,expectedMorphs,asset);
    if(!b.ok)return {ok:false,side:'B',reason:b.reason,details:b};
    const differences=expectedMorphs.map(name=>({name,a:a.weights[name]??0,b:b.weights[name]??0,delta:(b.weights[name]??0)-(a.weights[name]??0)}));
    const abs=differences.map(item=>Math.abs(item.delta));
    const changed=differences.filter(item=>item.delta!==0).length;
    return {ok:true,asset,morphCount:differences.length,changedCount:changed,maxAbsDelta:abs.length?Math.max(...abs):0,meanAbsDelta:abs.length?abs.reduce((sum,n)=>sum+n,0)/abs.length:0,differences:differences.sort((x,y)=>Math.abs(y.delta)-Math.abs(x.delta)||x.name.localeCompare(y.name))};
  }
  const api={compareSnapshots};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.AvatarExpressionCompare=api;
})(typeof globalThis!=='undefined'?globalThis:this);
