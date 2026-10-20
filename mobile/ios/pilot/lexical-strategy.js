"use strict";

let lexicalStrategyDraft = "",lexicalStrategyDraftKey=null;

async function lexicalStrategyCommand(operation, value = "") {
  const screen = state?.lexical_strategy;
  if (!screen || !state.item || (paused && operation !== "resume")) return;
  const payload = {session_id:state.session_id, item_id:state.item.id,
    revision:screen.revision, operation, value, elapsed_ms:Math.round(clock.elapsed())};
  return perform(async () => {
    let view;
    try { view = await request("lexical-strategy-step", payload); }
    catch (error) {
      const durable = await request("view").catch(() => null);
      if (!durable) throw error;
      if (!durable.finished && !durable.feedback
          && durable.lexical_strategy?.revision === payload.revision) {
        render(durable); throw error;
      }
      view = durable;
    }
    if (operation === "note" || operation === "answer") lexicalStrategyDraft = "";
    if (operation === "resume") paused = false;
    else if (operation === "pause") paused = true;
    render(view); clock.reset(paused);
  });
}

function renderLexicalStrategy(view) {
  const region = element("lexicalStrategy");
  region.replaceChildren();
  const key=JSON.stringify([view.session_id,view.item?.id,view.position,view.lexical_strategy?.phase,view.lexical_strategy?.note_index]);
  if(key!==lexicalStrategyDraftKey){lexicalStrategyDraft="";lexicalStrategyDraftKey=key;}
  const screen = view?.lexical_strategy;
  region.hidden = !screen || !view.item || Boolean(view.finished) || Boolean(view.feedback);
  if (region.hidden || screen.paused || paused) return;
  const paragraph = (text, className = "") => {
    const node = document.createElement("p"); node.textContent = text || "";
    if (className) node.className = className;
    region.append(node); return node;
  };
  const button = (label, callback, primary = false) => {
    const node = document.createElement("button"); node.type = "button";
    node.className = primary ? "" : "secondaryButton";
    node.textContent = label;
    node.onclick = callback; region.append(node); return node;
  };
  if (screen.phase === "notes") {
    paragraph(screen.instruction, "strategy-instruction");
    paragraph(screen.definition, "strategy-definition");
    const progress = document.createElement("p");
    progress.textContent = `Étape ${screen.note_index + 1} sur ${screen.total_notes}`;
    region.append(progress);
    screen.notes.forEach((note, index) => paragraph(`${index + 1}. ${note || "(aucune note)"}`));
    paragraph(screen.prompt);
    const field = document.createElement("textarea");
    field.rows = 2; field.maxLength = 2000; field.value = lexicalStrategyDraft;
    field.setAttribute("aria-label", screen.prompt || "Ta note");
    field.addEventListener("input", () => { lexicalStrategyDraft = field.value; });
    region.append(field);
    button("Enregistrer cette note", () => lexicalStrategyCommand("note", field.value), true);
  } else if (screen.phase === "answer") {
    paragraph("Tes notes ne sont pas notées : elles servent seulement à retrouver le mot.");
    if (screen.retry_feedback) paragraph(screen.retry_feedback, "secondary");
    screen.notes.forEach((note, index) => paragraph(`${index + 1}. ${note || "(aucune note)"}`));
    paragraph(screen.question);
    const field = document.createElement("input");
    field.type = "text"; field.autocomplete = "off"; field.maxLength = 500;
    field.value = lexicalStrategyDraft; field.setAttribute("aria-label", screen.question || "Le mot retrouvé");
    field.addEventListener("input", () => { lexicalStrategyDraft = field.value; });
    field.addEventListener("keydown", event => {
      if (event.key === "Enter" && field.value.trim()) lexicalStrategyCommand("answer", field.value);
    });
    region.append(field);
    button("Valider le mot", () => lexicalStrategyCommand("answer", field.value), true);
  }
  region.querySelector("textarea, input, button")?.focus();
}
