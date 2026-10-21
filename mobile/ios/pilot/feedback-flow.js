"use strict";
let feedbackTimer=null,feedbackKey=null,feedbackHeld=false;
function stopFeedbackFlow(){clearTimeout(feedbackTimer);feedbackTimer=null;}
function feedbackFlowKey(view){return JSON.stringify([view?.session_id,view?.item?.id||view?.item_id,view?.position,view?.contextes?.pass,view?.immediate?.phase,view?.protocol?.phase,Boolean(view?.feedback)]);}
function feedbackCanAdvance(view){
  if(!view||view.finished||paused||view.contextes?.paused||view.protocol?.paused||view.memory?.paused)return false;
  if(view.immediate)return Boolean(view.item_id)&&view.immediate.phase==='feedback';
  if(!view.item)return false;
  if(view.protocol&&!view.feedback)return ['P-retour','Q-retour'].includes(view.protocol.phase);
  if(view.contextes)return view.contextes.phase==='feedback'&&!view.contextes.image_failed&&(!view.contextes.image||view.contextes.reveal_recorded);
  return Boolean(view.feedback);
}
function renderFeedbackFlow(view){
  const key=feedbackFlowKey(view);
  if(key!==feedbackKey){stopFeedbackFlow();feedbackKey=key;feedbackHeld=false;}
  const available=feedbackCanAdvance(view);
  element('holdFeedback').hidden=!available;
  element('holdFeedback').textContent=feedbackHeld?'Suite automatique':'Prendre le temps';
  element('feedbackFlowStatus').textContent=available?(feedbackHeld?'À ton rythme.':'La suite arrive automatiquement.') : '';
  if(!available)stopFeedbackFlow();
}
function armFeedbackFlow(){
  renderFeedbackFlow(state);
  if(busy||feedbackHeld||feedbackTimer!==null||!feedbackCanAdvance(state))return;
  const key=feedbackKey;
  const text=state.immediate?element('immediate').textContent:state.protocol&&!state.feedback?state.protocol.paragraphs.join(' '):element('feedback').textContent||state.contextes?.question||'';
  const words=text.trim().split(/\s+/).filter(Boolean).length;
  const delay=Math.min(12000,Math.max(state.feedback?.correcte===false||state.immediate?.correction?.exacte===false?4000:2200,1200+words*350));
  function advance(){
    feedbackTimer=null;
    if(key!==feedbackKey||feedbackHeld||busy||!feedbackCanAdvance(state))return;
    if(speechToken||audioBusy){feedbackTimer=setTimeout(advance,250);feedbackTimer?.unref?.();return;}
    if(state.immediate)immediateCommand('continue');else if(state.contextes)contextesCommand('next');else if(state.protocol&&!state.feedback)protocolCommand('continue');else element('next').onclick();
  }
  feedbackTimer=setTimeout(advance,delay);feedbackTimer?.unref?.();
}
function toggleFeedbackHold(){
  stopFeedbackFlow();feedbackHeld=!feedbackHeld;renderFeedbackFlow(state);
  if(!feedbackHeld)armFeedbackFlow();
}
