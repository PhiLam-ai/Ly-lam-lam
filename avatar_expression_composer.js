/* Conservative facial morph composition and procedural/API coordination. */
(function(root){'use strict';
  function weight(v){const n=typeof v==='number'?v:Number(v);return Number.isFinite(n)?Math.max(0,Math.min(1,n)):0;}
  function composeExpressionWeights(input){
    const out={}; if(!input||typeof input!=='object'||Array.isArray(input)) return out;
    for(const [key,value] of Object.entries(input)) out[key]=weight(value);
    // Articulation shapes compete; preserve the stronger lip pose.
    const fv=out.lip_fv||0, round=out.lip_round||0;
    if(fv>0&&round>0){if(fv>=round)out.lip_round=round*(1-fv*.85);else out.lip_fv=fv*(1-round*.85);}
    const press=out.lip_press||0;
    if(out.mouth_open!==undefined)out.mouth_open=weight(out.mouth_open*(1-press*.55));
    const articulation=Math.max(out.lip_fv||0,out.lip_round||0);
    if(out.smile!==undefined)out.smile=weight(out.smile*(1-articulation*.38));
    if(out.cheek_raise!==undefined)out.cheek_raise=weight(out.cheek_raise*(1-articulation*.12));
    // Clamp jaw motion to the available mouth opening; never increase a requested value.
    // Legacy contract retained: out.jaw_hinge=Math.min(out.jaw_hinge||0,out.jaw_open||0)
    if(out.jaw_open!==undefined)out.jaw_open=Math.min(out.jaw_open, out.mouth_open===undefined?out.jaw_open:out.mouth_open);
    if(out.jaw_hinge!==undefined)out.jaw_hinge=Math.min(out.jaw_hinge,out.jaw_open===undefined?out.jaw_hinge:out.jaw_open);
    return out;
  }
  function composeAvatarFrame(apiWeights, proceduralBlink){
    const merged={};
    if(apiWeights&&typeof apiWeights==='object'&&!Array.isArray(apiWeights)){
      for(const [key,value] of Object.entries(apiWeights)) merged[key]=weight(value);
    }
    // Procedural blink augments, but never cancels, an API-requested eye closure.
    const blink=weight(proceduralBlink);
    merged.blink_left=Math.max(merged.blink_left||0,blink);
    merged.blink_right=Math.max(merged.blink_right||0,blink);
    return composeExpressionWeights(merged);
  }
  const api={composeExpressionWeights,composeAvatarFrame,weight};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.AvatarExpressionComposer=api;
})(typeof globalThis!=='undefined'?globalThis:this);
