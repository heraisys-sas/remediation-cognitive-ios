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
  if(view.activity==='anglais'||view.activity==='python'||view.immediate)return '';
  if(view.activity==='deduction')return textePourLectureDeduction(view.item.contenu);
  if(view.lexical_strategy)return [view.lexical_strategy.instruction,view.lexical_strategy.definition,view.lexical_strategy.prompt,view.lexical_strategy.question].filter(Boolean).join('\n');
  if(view.functional)return [view.functional.consigne,view.functional.etape?.texte].filter(Boolean).join('\n');
  if(view.attention)return [view.attention.instruction,view.attention.objective,view.attention.criterion,view.attention.prompt,view.attention.message?.text,view.attention.point?.state].filter(Boolean).join('\n');
  if(view.comparison)return (view.comparison.documents||[]).flatMap(doc=>[doc.titre,...doc.lignes.map(line=>`${line.label} : ${line.texte}`)]).join('\n');
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
  if(!view?.item||view.finished||view.feedback||paused||view.protocol?.paused||view.memory?.paused||view.contextes||view.immediate||view.lexical_strategy||view.functional||view.comparison||view.attention||view.activity==="deduction"||view.activity==="python"||view.activity==="anglais") return null;
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
  stopMemoryAudio();
  abortAutoLexical();
  notifyAutoReading(false);
  audioGeneration+=1;
  const active=Boolean(speechToken||dictationDraft||immediateSpeechToken);
  immediateStopTimer();
  if(immediateSpeechToken){immediateSpeechToken=null;clearTimeout(immediateSpeechWatchdog);const resolve=immediateSpeechResolve;immediateSpeechResolve=null;resolve?.();}
  speechToken=null; unlockDictation();
  if(active) return speechRequest("cancel").catch(()=>{});
  return null;
}
function renderAudioButton(button, label, kind, active, compact) {
  button.textContent = compact ? "" : label;
  button.className = compact ? "secondaryButton audioIconButton" : "secondaryButton";
  button.setAttribute("aria-label", label);
  button.setAttribute("title", label);
  button.setAttribute("aria-pressed", String(Boolean(active)));
  if (!compact) return;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24"); svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", active ? "M6 6h12v12H6Z" : kind === "microphone"
    ? "M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0V5ZM6 11v1a6 6 0 0 0 12 0v-1M12 18v4M8 22h8"
    : "M11 4 6 8H3v8h3l5 4V4ZM15 8a6 6 0 0 1 0 8M18 5a10 10 0 0 1 0 14");
  svg.append(path); button.append(svg);
}
function renderSpeechControls(view) {
  const key=audioContextKey(view);
  if(speechViewKey!==key) { element("audioStatus").textContent=""; speechViewKey=key; }
  const target=dictationTarget(view), text=speechTextForView(view);
  if(dictationDraft&&(dictationDraft.key!==audioContextKey(view)||dictationDraft.field!==target)) stopSpeechForTransition();
  element("audioControls").hidden=!view?.item||Boolean(view.finished)||paused||!speechCapabilities;
  element("listen").hidden=!text||!speechCapabilities?.speech;
  const compact = view?.activity === "calcul-mental";
  renderAudioButton(element("listen"), speechToken?"Arrêter la lecture":compact?"Écouter la question":"Écouter", "speaker", speechToken, compact);
  element("listen").disabled=audioBusy;
  element("dictate").hidden=!target||!speechCapabilities?.on_device_dictation;
  renderAudioButton(element("dictate"), autoLexical?"Répondre au clavier":dictationDraft?"Arrêter la dictée":"Dicter", "microphone", dictationDraft, compact);
  const inlineMic = compact && !element("dictate").hidden;
  element("answerEntry").className = inlineMic ? "answerEntry withMicrophone" : "answerEntry";
  (inlineMic ? element("answerEntry") : element("audioControls")).append(element("dictate"));
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
  if(window.immediateNativeSpeechEvent?.(event))return;
  if(memoryAudio&&event?.token===memoryAudio.token){memoryNativeSpeechEvent(event);return;}
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
