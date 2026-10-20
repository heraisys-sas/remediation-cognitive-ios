"use strict";
let speechCapabilities=null, speechToken=null, dictationDraft=null, audioBusy=false, audioSerial=0, speechViewKey=null, audioGeneration=0;
function audioContextKey(view) {
  return JSON.stringify([view?.session_id,view?.item?.id,view?.position,view?.protocol?.phase,view?.protocol?.revision,
    view?.memory?.phase,view?.memory?.revision,Boolean(view?.feedback),view?.hints_used]);
}
function speechTextForView(view) {
  if(!view?.item||view.finished||paused||view.memory?.paused||view.contextes?.paused||view.protocol?.paused) return "";
  if(view.feedback) return view.feedback.sequence?pqrstFeedbackLines(view.feedback).join("\n"):
    [view.feedback.feedback,view.feedback.attendue!=null?`Réponse : ${view.feedback.attendue}.`:null].filter(Boolean).join("\n");
  if(view.memory) return [view.memory.instruction,view.memory.question].filter(Boolean).join("\n");
  if(view.contextes) return [view.contextes.instruction,view.contextes.question].filter(Boolean).join("\n");
  if(view.protocol) return [...view.protocol.paragraphs,...(view.protocol.options||[])].filter(Boolean).join("\n");
  const content=view.item.contenu;
  const parts=[content.consigne,content.enonce];
  if(isChoiceActivity(view)) parts.push(content.document,...(content.plan||[]),...(content.options||[]));
  if(view.activity==="acces-lexical") parts.push(...(content.indices||[]).slice(0,view.hints_used||0).map(hint=>hint.texte));
  if(view.reprise&&view.reprise_attendue!=null) parts.push(`Reprise avec la réponse déjà fournie : ${view.reprise_attendue}.`);
  if(view.feedback) parts.push(view.feedback.feedback,view.feedback.attendue!=null?`Réponse : ${view.feedback.attendue}.`:null);
  return parts.filter(Boolean).join("\n");
}
function dictationTarget(view) {
  if(!view?.item||view.finished||view.feedback||paused||view.protocol?.paused||view.memory?.paused||view.contextes) return null;
  if(view.protocol) return view.protocol.input_label?element("protocol-answer"):null;
  if(isChoiceActivity(view)) return null;
  if(view.memory&&view.memory.phase!=="question") return null;
  return element("answer");
}
async function speechRequest(operation,data={}) {
  if(!window.webkit?.messageHandlers?.speech) throw Error("Les fonctions vocales sont disponibles dans l’application iPhone.");
  return window.webkit.messageHandlers.speech.postMessage({operation,...data});
}
function unlockDictation() {
  if(!dictationDraft) return;
  dictationDraft.field.readOnly=false;
  if(typeof dictationDraft.field.oninput==="function") dictationDraft.field.oninput();
  dictationDraft=null;
}
function stopSpeechForTransition() {
  abortAutoLexical();
  notifyAutoReading(false);
  audioGeneration+=1;
  const active=Boolean(speechToken||dictationDraft);
  speechToken=null; unlockDictation();
  if(active) return speechRequest("cancel").catch(()=>{});
  return null;
}
function renderSpeechControls(view) {
  const key=audioContextKey(view);
  if(speechViewKey!==key) { element("audioStatus").textContent=""; speechViewKey=key; }
  const target=dictationTarget(view), text=speechTextForView(view);
  if(dictationDraft&&(dictationDraft.key!==audioContextKey(view)||dictationDraft.field!==target)) stopSpeechForTransition();
  element("audioControls").hidden=!view?.item||Boolean(view.finished)||paused||!speechCapabilities;
  element("listen").hidden=!text||!speechCapabilities?.speech;
  element("listen").textContent=speechToken?"Arrêter la lecture":"Écouter";
  element("listen").disabled=audioBusy;
  element("dictate").hidden=!target||!speechCapabilities?.on_device_dictation;
  element("dictate").textContent=autoLexical?"Répondre au clavier":dictationDraft?"Arrêter la dictée":"Dicter";
  element("dictate").disabled=audioBusy||dictationDraft?.status==="finishing";
  // Recalculer le verrou après perform : son instantané peut dater de la capture.
  element("validate").disabled=busy||Boolean(dictationDraft);
  if(!busy&&!dictationDraft&&view?.protocol?.input_label&&target&&typeof target.oninput==="function") target.oninput();
  if(dictationDraft) {
    dictationDraft.field.readOnly=true;
    for(const id of ["validate","protocol-respond","protocol-reread"]) {
      const button=document.getElementById(id);if(button) button.disabled=true;
    }
  }
}
async function audioOperation(operation) {
  if(audioBusy||busy||paused) return;
  audioBusy=true; element("audioStatus").textContent="";
  try {await operation();}
  catch(error) {speechToken=null;notifyAutoReading(false);unlockDictation();element("audioStatus").textContent=String(error.message||error);}
  finally {audioBusy=false;renderSpeechControls(state);armAutoLexical();}
}
async function listenVisibleText() {
  return audioOperation(async()=>{
    if(speechToken) {await speechRequest("stop-speaking");return;}
    const text=speechTextForView(state), key=audioContextKey(state);
    if(!text) return;
    const stopped=stopSpeechForTransition(), generation=audioGeneration;
    if(stopped) await stopped;
    if(generation!==audioGeneration||paused||busy||audioContextKey(state)!==key) return;
    const token=`read-${++audioSerial}`;speechToken=token;
    notifyAutoReading(true);
    await speechRequest("speak",{token,text:text.slice(0,12000)});
  });
}
async function dictateAnswer() {
  if(autoLexical){autoLexical.manuel();return;}
  return audioOperation(async()=>{
    if(dictationDraft) {dictationDraft.status="finishing";await speechRequest("stop-dictation");return;}
    const field=dictationTarget(state), key=audioContextKey(state); if(!field) return;
    const stopped=stopSpeechForTransition(), generation=audioGeneration;
    if(stopped) await stopped;
    if(generation!==audioGeneration||paused||busy||audioContextKey(state)!==key||dictationTarget(state)!==field) return;
    const token=`dictate-${++audioSerial}`;
    dictationDraft={token,field,key:audioContextKey(state),prefix:field.value||"",status:"authorizing"};
    renderSpeechControls(state);
    element("audioStatus").textContent="Préparation de la dictée…";
    await speechRequest("start-dictation",{token});
  });
}
window.nativeSpeechEvent=event=>{
  if(receiveAutoSpeech(event))return;
  if(event?.kind==="speech"&&event.token===speechToken) {
    if(["finished","stopped"].includes(event.status)) {speechToken=null;notifyAutoReading(false);}
    renderSpeechControls(state);return;
  }
  if(event?.kind!=="dictation"||event.token!==dictationDraft?.token||dictationDraft.key!==audioContextKey(state)) return;
  const draft=dictationDraft;
  if(event.text) {
    draft.field.value=[draft.prefix.trimEnd(),String(event.text).trim()].filter(Boolean).join(" ").slice(0,2000);
    if(typeof draft.field.oninput==="function") draft.field.oninput();
  }
  draft.status=event.status;
  const messages={listening:"Je t’écoute…",partial:"Je t’écoute…",finishing:"Fin de la dictée…",
    finished:"Vérifie le texte, puis valide ta réponse.",cancelled:"Dictée arrêtée. Vérifie le texte avant de valider.",
    interrupted:"Dictée interrompue. Vérifie le texte ou utilise le clavier.",
    denied:"Dictée non autorisée. Tu peux utiliser le clavier ou l’autoriser dans Réglages.",
    unavailable:"La dictée est indisponible sur cet appareil pour le moment. Tu peux utiliser le clavier."};
  element("audioStatus").textContent=messages[event.status]||"";
  if(!["listening","partial","finishing"].includes(event.status)) unlockDictation();
  renderSpeechControls(state);
};
async function initializeSpeech() {
  try {speechCapabilities=await speechRequest("capabilities");}
  catch {speechCapabilities=null;}
  if(state) renderSpeechControls(state);
  await initializeVoiceSettings();
}
