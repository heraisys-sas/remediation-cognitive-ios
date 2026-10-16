"use strict";
const element = id => document.getElementById(id);
let state = null, startedAt = performance.now(), busy = false, paused = false;
async function request(action, data = {}) {
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
  element("start").hidden = Boolean(view.started && !view.finished);
  element("finish").hidden = !view.started || Boolean(view.finished);
  element("exercise").hidden = !view.item || paused;
  element("summary").hidden = !view.finished;
  if (view.finished) {
    const summary = view.summary.resume;
    element("summaryText").textContent = `${summary.items} questions travaillées, dont ${summary.correctes} réussies à la première réponse retenue.`;
    element("start").textContent = "Nouvelle séance";
    return;
  }
  if (!view.item) return;
  element("position").textContent = `${view.reprise ? "Reprise après correction · " : ""}Question ${view.position} sur ${view.total}`;
  element("question").textContent = view.item.contenu.enonce;
  element("methodText").textContent = view.item.contenu.methode || "";
  element("method").hidden = !view.item.contenu.methode;
  element("answerForm").hidden = Boolean(view.feedback);
  element("next").hidden = !view.feedback;
  element("feedback").textContent = view.feedback ? `${view.feedback.feedback || ""}${view.feedback.attendue != null ? " Réponse : " + view.feedback.attendue + "." : ""}` : "";
}
element("start").onclick = () => perform(async () => {
  await request("start"); render(await request("view")); startedAt = performance.now();
});
element("answerForm").onsubmit = event => {
  event.preventDefault();
  if (!element("answer").value.trim() || !state?.item || paused) return;
  perform(async () => {
    await request("answer", {session_id: state.session_id, item_id: state.item.id,
      answer: element("answer").value, elapsed_ms: Math.round(performance.now() - startedAt)});
    element("answer").blur(); render(await request("view"));
  });
};
element("next").onclick = () => perform(async () => {
  const view = await request("next");
  element("answer").value = ""; element("method").open = false;
  if (!view.item) { await request("finish", {session_id: state.session_id}); render(await request("view")); }
  else { render(view); startedAt = performance.now(); element("question").focus(); }
});
element("finish").onclick = () => perform(async () => {
  await request("finish", {session_id: state.session_id}); render(await request("view"));
});
window.pauseForInterruption = () => { paused = true; element("exercise").hidden = true; element("resume").hidden = false; };
document.addEventListener("visibilitychange", () => { if (document.hidden && state?.item) window.pauseForInterruption(); });
element("resume").onclick = () => {
  paused = false; element("resume").hidden = true; if (state) render(state);
};
perform(async () => render(await request("view")));
