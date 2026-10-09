/* Bounded retry policy for the avatar state API. */
(function(root){'use strict';
  function positive(value,fallback){const n=Number(value);return Number.isFinite(n)&&n>0?n:fallback;}
  function createRetryPolicy(options={}){
    const base=positive(options.baseDelayMs,1200), cap=Math.max(base,positive(options.maxDelayMs,12000));
    const factor=positive(options.factor,2); let failures=0;
    function success(){failures=0;return failures;}
    function failure(){failures=Math.min(failures+1,30);return failures;}
    function delay(){return Math.min(cap,base*Math.pow(factor,Math.max(0,failures-1)));}
    function reset(){failures=0;}
    return {success,failure,delay,reset,get failures(){return failures;}};
  }
  const api={createRetryPolicy};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.AvatarApiRecovery=api;
})(typeof globalThis!=='undefined'?globalThis:this);
