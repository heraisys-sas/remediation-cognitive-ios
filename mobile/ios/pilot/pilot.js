"use strict";
const element = id => document.getElementById(id);
let state = null, busy = false, paused = false;
const clock = new ActiveClock();
async function request(action, data = {}) {
  if (!window.webkit?.messageHandlers?.runtime) {
    throw new Error("Pour utiliser les exercices, ouvre l’application Remédiation sur l’iPhone ou dans le simulateur Xcode. Cette page seule affiche uniquement l’interface.");
  }
  return window.webkit.messageHandlers.runtime.postMessage({action, ...data});
}
async function perform(operation) {
  if (busy) return;
  busy = true;
  document.querySelectorAll("button").forEach(button => { button.disabled = true; });
  element("error").textContent = "";
  element("status").textContent = "Enregistrement sur l’appareil…";
  try { await operation(); }
  catch (error) { element("error").textContent = String(error.message || error); }
  finally {
    busy = false;
    element("status").textContent = "";
    document.querySelectorAll("button").forEach(button => { button.disabled = false; });
    if (paused) { element("exercise").hidden = true; element("resume").hidden = false; }
  }
}
function render(view) {
  state = view;
  element("activityChoice").hidden = Boolean(view.started && !view.finished);
  if (view.title) { document.querySelector("h1").textContent = view.title; document.title = view.title; }
  element("start").hidden = Boolean(view.started && !view.finished);
  element("finish").hidden = !view.started || Boolean(view.finished);
  element("exercise").hidden = !view.item || paused;
  element("summary").hidden = !view.finished;
  element("stopProposal").hidden = !view.arret_propose || Boolean(view.finished);
  element("summaryAdvice").hidden = !view.finished || !view.summary?.arret_propose;
  if (view.finished) {
    const summary = view.summary.resume;
    element("summaryText").textContent = `${summary.items} questions travaillées, dont ${summary.correctes} réussies à la première réponse retenue.`;
    if (summary.assistees != null) element("summaryText").textContent += ` ${summary.sans_aide} retrouvées sans aide ; ${summary.assistees} avec le mot affiché.`;
    element("start").textContent = "Nouvelle séance";
    return;
  }
  if (!view.item) return;
  element("position").textContent = `${view.reprise ? "Reprise après correction · " : ""}Question ${view.position} sur ${view.total}`;
  element("question").textContent = view.item.contenu.enonce;
  element("repriseSupport").hidden = !view.reprise || view.reprise_attendue == null;
  element("repriseSupport").textContent = view.reprise_attendue != null
    ? `Reprise avec la réponse déjà fournie : ${view.reprise_attendue}. Tu peux t’appuyer dessus.` : "";
  element("methodText").textContent = view.item.contenu.methode || "";
  element("method").hidden = !view.item.contenu.methode;
  const hints = view.item.contenu.indices || [];
  const lexical = view.item.type === "rappel-indice";
  element("lexicalHelp").hidden = !lexical || Boolean(view.feedback) || Boolean(view.reprise);
  element("hints").textContent = hints.slice(0, view.hints_used || 0).map(hint => hint.texte).join("\n");
  element("hint").hidden = (view.hints_used || 0) >= hints.length;
  element("answerForm").hidden = Boolean(view.feedback);
  element("next").hidden = !view.feedback;
  element("feedback").textContent = view.feedback ? `${view.feedback.feedback || ""}${view.feedback.attendue != null ? " Réponse : " + view.feedback.attendue + "." : ""}` : "";
}
element("start").onclick = () => perform(async () => {
  await request("start", {activity: element("activity").value || "calcul-mental"});
  let view = await request("view");
  if (!view.item && !view.finished) { await request("finish", {session_id:view.session_id}); view = await request("view"); }
  render(view); element("answer").value = ""; clock.reset(paused);
});
element("activity").onchange = () => {
  document.querySelector("h1").textContent = element("activity").value === "acces-lexical" ? "Retrouver le mot" : "Calcul mental";
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
  if (!element("answer").value.trim() || !state?.item || paused) return;
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
window.pauseForInterruption = () => { clock.pause(); paused = true; element("exercise").hidden = true; element("resume").hidden = false; };
document.addEventListener("visibilitychange", () => { if (document.hidden && state?.item) window.pauseForInterruption(); });
element("resume").onclick = () => {
  clock.resume(); paused = false; element("resume").hidden = true; if (state) render(state);
};
perform(async () => { render(await request("view")); clock.reset(paused); });
