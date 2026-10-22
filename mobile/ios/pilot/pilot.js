"use strict";
const element = id => document.getElementById(id);
let state = null, busy = false, paused = false;
let pendingProtocolPause = false;
let lexicalHelpKey=null, methodKey=null;
const clock = new ActiveClock();
async function request(action, data = {}) {
  if (!window.webkit?.messageHandlers?.runtime) {
    throw new Error("Pour utiliser les exercices, ouvre l’application Remédiation sur l’iPhone ou dans le simulateur Xcode. Cette page seule affiche uniquement l’interface.");
  }
  return window.webkit.messageHandlers.runtime.postMessage({action, ...data});
}
async function perform(operation) {
  if (busy) return;
  stopFeedbackFlow();
  busy = true;
  const disabledBefore = new Map();
  document.querySelectorAll("button").forEach(button => { disabledBefore.set(button, button.disabled); button.disabled = true; });
  element("error").textContent = "";
  element("status").textContent = "Enregistrement sur l’appareil…";
  try { const stopAudio=stopSpeechForTransition(); if(stopAudio) await stopAudio; await operation(); }
  catch (error) { element("error").textContent = String(error.message || error); }
  finally {
    try { await flushProtocolPause(); }
    catch (error) { element("error").textContent ||= String(error.message || error); }
    busy = false;
    element("status").textContent = "";
    document.querySelectorAll("button").forEach(button => { if (disabledBefore.has(button)) button.disabled = disabledBefore.get(button); });
    if (paused) { element("exercise").hidden = true; element("resume").hidden = false; }
    renderVoiceSettingsControls();renderHomeControls();
    if (state) { renderSpeechControls(state); armAutoLexical(); armFeedbackFlow(); }
  }
}
function render(view) {
  state = view;
  renderFeedbackFlow(view);
  const currentMethodKey=JSON.stringify([view.session_id,view.item?.id,view.position,Boolean(view.reprise)]);
  if(currentMethodKey!==methodKey){element("method").open=false;methodKey=currentMethodKey;}
  if (view.finished) paused = false;
  if (view.protocol?.paused || view.contextes?.paused || view.memory?.paused || view.lexical_strategy?.paused || view.functional?.paused || view.comparison?.paused || view.attention?.paused) paused = true;
  const activeSession=Boolean(view.started&&!view.finished);
  element("sessionOptions").hidden=!activeSession;
  element("intro").hidden=activeSession;
  if(!activeSession)element("sessionOptions").open=false;
  renderImmediate(view);
  if(view.immediate){
    for(const id of ["question","position","lexicalHelp","method","repriseSupport","answerForm","protocol","protocolDictation","contextes","memory","choices","deduction","lexicalStrategy","functional","comparison","attention","feedback","next","audioControls"])element(id).hidden=true;
    element("resume").hidden=!paused||Boolean(view.finished);
    document.title=view.finished?"Remédiation":view.title;
    element("activityChoice").hidden=!view.finished;element("exercise").hidden=Boolean(view.finished)||paused;
    element("start").hidden=true;element("finish").hidden=Boolean(view.finished);element("summary").hidden=!view.finished;
    element("stopProposal").hidden=true;
    element("answerForm").hidden=true;element("next").hidden=true;element("audioControls").hidden=true;
    document.querySelector("h1").textContent=view.finished?"Remédiation":view.title;
    if(view.finished)element("summaryText").textContent="Bloc de mémoire enregistré. Les premières réponses, aides et interruptions sont conservées séparément.";
    renderHomeControls();return;
  }
  element("question").hidden=false;element("position").hidden=false;element("feedback").hidden=false;
  renderLexicalStrategy(view);renderFunctional(view);renderComparison(view);renderAttention(view);renderDeduction(view);
  renderContextes(view);
  renderChoices(view);
  renderMemory(view);
  element("resume").hidden = !paused || Boolean(view.finished);
  element("activityChoice").hidden = Boolean(view.started && !view.finished);
  if (!view.started || view.finished) {document.querySelector("h1").textContent="Remédiation";document.title="Remédiation";}
  else if (view.title) { document.querySelector("h1").textContent = view.title; document.title = view.title; }
  element("start").hidden = true;
  element("finish").hidden = !view.started || Boolean(view.finished);
  element("exercise").hidden = !view.item || paused;
  element("summary").hidden = !view.finished;
  element("stopProposal").hidden = !view.arret_propose || Boolean(view.finished);
  element("summaryAdvice").hidden = !view.finished || !view.summary?.arret_propose;
  if (view.finished) {
    renderSpeechControls(view);
    const summary = view.summary.resume;
    element("summaryText").textContent = `${summary.items} questions travaillées, dont ${summary.correctes} réussies à la première réponse retenue.`;
    if (view.activity === "memoire-source") element("summaryText").textContent = `${summary.items} rappel(s) final(aux), dont ${summary.correctes} réussi(s). La découverte ne compte pas dans la progression.`;
    if (view.activity === "pqrst-guide") element("summaryText").textContent = `${summary.items} texte(s) travaillé(s). Les résultats par étape sont conservés.`;
    if (view.activity === "acces-lexical" && summary.assistees != null) element("summaryText").textContent += ` ${summary.sans_aide} retrouvées sans aide ; ${summary.assistees} avec le mot affiché.`;
    element("start").textContent = "Nouvelle séance";
    return;
  }
  if (!view.item) { renderSpeechControls(view); return; }
  element("position").textContent = `${view.reprise ? "Reprise après correction · " : ""}Question ${view.position} sur ${view.total}`;
  element("question").textContent = view.item.contenu.enonce;
  const isPqrst = view.item.type === "pqrst-mise-en-oeuvre";
  renderPqrstProtocol(view);
  element("repriseSupport").hidden = isPqrst || !view.reprise || view.reprise_attendue == null;
  element("repriseSupport").textContent = view.reprise_attendue != null
    ? `Reprise avec la réponse déjà fournie : ${view.reprise_attendue}. Tu peux t’appuyer dessus.` : "";
  element("methodText").textContent = view.item.contenu.methode || "";
  element("method").hidden = !view.item.contenu.methode;
  if (!view.memory) element("answer").inputMode = view.inputmode || "text";
  const hints = view.item.contenu.indices || [];
  const lexical = view.item.type === "rappel-indice";
  const helpKey=JSON.stringify([view.session_id,view.item.id,view.position,Boolean(view.reprise)]);
  if(helpKey!==lexicalHelpKey){element("lexicalHelp").open=false;lexicalHelpKey=helpKey;}
  element("lexicalHelp").hidden = !lexical || Boolean(view.feedback) || Boolean(view.reprise);
  element("hints").textContent = hints.slice(0, view.hints_used || 0).map(hint => hint.texte).join("\n");
  element("hint").hidden = (view.hints_used || 0) >= hints.length;
  element("answerForm").hidden = Boolean(view.memory && view.memory.phase !== "question") || Boolean(view.memory?.paused) || Boolean(view.contextes) || isPqrst || isChoiceActivity(view) || Boolean(view.feedback) || Boolean(view.lexical_strategy||view.functional||view.comparison||view.attention) || view.activity==="deduction" || Boolean(view.memory?.options?.length);
  element("next").hidden = Boolean(view.contextes) || !view.feedback;
  element("feedback").textContent = view.feedback ? `${view.feedback.feedback === "Bien joué, réponse correcte !" ? "Réponse correcte !" : view.feedback.feedback || ""}${view.feedback.attendue != null ? " Réponse : " + view.feedback.attendue + "." : ""}` : "";
  if (!view.feedback && view.retry_feedback) element("feedback").textContent = view.retry_feedback;
  if (isPqrst && view.feedback) element("feedback").textContent = pqrstFeedbackLines(view.feedback).join("\n\n");
  if (view.feedback?.correcte === true) {
    const mark = document.createElement("span"); mark.className = "successMark";
    mark.setAttribute("aria-hidden", "true"); element("feedback").append(mark);
  }
  renderSpeechControls(view);
}
element("start").onclick = () => perform(async () => {
  const activity=element("activity").value||"calcul-mental";
  await authorizeAutoLexical(activity);
  const params=activity.startsWith("mi-")?{parametres:activity==="mi-code"?{modalite:element("miModality").value||"visuelle"}:activity==="mi-changement"?{condition:element("miCondition").value||"forme"}:{}}:{};
  await request("start", {activity,...params});
  let view = await request("view");
  if (!view.item && !view.finished) { await request("finish", {session_id:view.session_id}); view = await request("view"); }
  bindAutoLexicalSession(view);
  render(view); element("answer").value = ""; clock.reset(paused);
});
element("activity").onchange = () => {
  document.querySelector("h1").textContent = {"acces-lexical":"Retrouver le mot", "pqrst-guide":"PQRST guidé", "memoire-source":"Retrouver le contexte", "choisir-plan":"Choisir un plan", "auto-instruction":"Se guider avant d’agir", "verifier-plan":"Vérifier un plan", "chercher-information":"Chercher dans un document", "chiffres-endroit":"Chiffres dans l’ordre", "chiffres-envers":"Chiffres en ordre inverse", "mots":"Mots — ordre et ordre inverse", "associations":"Associations mot–nombre", "position":"Position dans une séquence"}[element("activity").value] || "Calcul mental";
};
element("hint").onclick = () => perform(async () => {
  if (!state?.item || paused) return;
  render(await request("hint", {session_id:state.session_id, item_id:state.item.id}));
});
element("reveal").onclick = () => perform(async () => {
  if (!state?.item || paused) return;
  await request("reveal", {session_id:state.session_id, item_id:state.item.id, elapsed_ms:Math.round(clock.elapsed())});
  element("answer").blur(); render(await request("view"));
});
element("answerForm").onsubmit = event => {
  event.preventDefault();
  if (!element("answer").value.trim() || !state?.item || paused || busy || audioBusy || dictationDraft) return;
  if (state.memory) return memoryCommand("answer", element("answer").value);
  perform(async () => {
    await request("answer", {session_id: state.session_id, item_id: state.item.id,
      answer: element("answer").value, elapsed_ms: Math.round(clock.elapsed())});
    element("answer").blur(); render(await request("view"));
  });
};
element("next").onclick = () => perform(async () => {
  const view = await request("next");
  element("answer").value = ""; element("method").open = false;
  if (!view.item) { await request("finish", {session_id: state.session_id}); render(await request("view")); }
  else { render(view); clock.reset(paused); element("question").focus(); }
});
element("finish").onclick = () => perform(async () => {
  await request("finish", {session_id: state.session_id}); render(await request("view"));
});
element("continueChoice").onclick = () => perform(async () => render(await request("dismiss-stop-proposal")));
async function protocolCommand(operation, value = null) {
  if (!state?.protocol || (paused && operation !== "resume")) return;
  const payload = {session_id:state.session_id, item_id:state.item.id, revision:state.protocol.revision,
    operation, value, elapsed_ms:Math.round(clock.elapsed())};
  const previousView = state;
  return perform(async () => {
    let view;
    try { view = await request("pqrst-step", payload); }
    catch (error) {
      // Une réponse native perdue n'annule pas forcément sa transaction.
      // Relire l'état durable évite de rester bloqué sur une ancienne révision.
      const durable = await request("view").catch(() => null);
      if (!durable) throw error;
      if (!durable.finished && !durable.feedback && durable.protocol?.revision === payload.revision) {
        render(durable); throw error;
      }
      view = durable;
    }
    if (["respond", "reread"].includes(operation)) clearPqrstDraft(previousView);
    if (operation === "resume") paused = false;
    render(view); clock.reset(paused);
    if (!paused && view.protocol) element("protocol-heading").focus();
  });
}
async function flushProtocolPause() {
  if (!pendingProtocolPause) return;
  let view = await request("view");
  if(view.immediate){
    view=await request("immediate-interrupt",{session_id:view.session_id,item_id:view.item_id,revision:view.immediate.revision});
  }
  for(const [field,action] of [["lexical_strategy","lexical-strategy-step"],["functional","functional-step"],["comparison","comparison-step"],["attention","attention-step"]]){
    if(view[field]&&!view[field].paused&&!view.feedback)view=await request(action,{session_id:view.session_id,item_id:view.item.id,revision:view[field].revision,operation:"pause",elapsed_ms:Math.round(clock.elapsed())});
  }
  if (view.memory && !view.memory.paused && !view.feedback) {
    view = await request("memory-step", {session_id:view.session_id,item_id:view.item.id,
      revision:view.memory.revision,operation:"pause",elapsed_ms:Math.round(clock.elapsed())});
  }
  if (view.contextes && !view.contextes.paused) {
    view = await request("contextes-step", {session_id:view.session_id, item_id:view.item.id,
      revision:view.contextes.revision, operation:"pause", elapsed_ms:Math.round(clock.elapsed())});
  }
  if (view.protocol && !view.protocol.paused && !["pret", "fin"].includes(view.protocol.phase)) {
    view = await request("pqrst-step", {session_id:view.session_id, item_id:view.item.id,
      revision:view.protocol.revision, operation:"pause", elapsed_ms:Math.round(clock.elapsed())});
  }
  pendingProtocolPause = false;
  render(view); clock.reset(paused);
}
window.pauseForInterruption = () => {
  stopSpeechForTransition();
  stopFeedbackFlow();
  stopContextesTimer(); stopMemoryTimer();
  clock.pause(); paused = true; element("exercise").hidden = true; element("resume").hidden = false;
  if (state?.immediate || state?.lexical_strategy || state?.functional || state?.comparison || state?.attention || state?.memory || state?.contextes || (state?.protocol && !state.protocol.paused && !["pret", "fin"].includes(state.protocol.phase))) {
    pendingProtocolPause = true;
    if (!busy) return perform(async () => {});
  }
};
document.addEventListener("visibilitychange", () => { if (document.hidden && state?.item) window.pauseForInterruption(); });
element("resume").onclick = async () => {
  if (pendingProtocolPause) await perform(flushProtocolPause);
  if (pendingProtocolPause) return;
  if(state?.immediate){paused=false;render(state);clock.reset(false);return;}
  if(state?.lexical_strategy?.paused)return lexicalStrategyCommand("resume");
  if(state?.functional?.paused)return functionalCommand("resume");
  if(state?.comparison?.paused)return comparisonCommand("resume");
  if(state?.attention?.paused)return attentionCommand("resume");
  if (state?.memory?.paused) return memoryCommand("resume");
  if (state?.contextes?.paused) return contextesCommand("resume");
  if (state?.protocol?.paused) return protocolCommand("resume");
  clock.resume(); paused = false; element("resume").hidden = true; if (state) {render(state);armAutoLexical();armFeedbackFlow();}
};
perform(async () => { render(await request("view")); clock.reset(paused); });

element("holdFeedback").onclick=toggleFeedbackHold;
element("listen").onclick=listenVisibleText;
element("dictate").onclick=dictateAnswer;
initializeSpeech();
initializeHomeSettings();
