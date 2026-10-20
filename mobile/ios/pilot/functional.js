"use strict";

const functionalDrafts = new Map();
const isFunctionalActivity = view => view?.activity === "actualiser-consigne";
const functionalKey = view => JSON.stringify([view?.session_id, view?.item?.id, view?.position]);

async function functionalCommand(operation, answer = null) {
  const screen = state?.functional;
  if (!screen || !state?.item || (paused && operation !== "resume")) return;
  const payload = {session_id: state.session_id, item_id: state.item.id, revision: screen.revision,
    operation, elapsed_ms: Math.round(clock.elapsed())};
  if (operation === "submit") payload.answer = answer;
  return perform(async () => {
    let view;
    try { view = await request("functional-step", payload); }
    catch (error) {
      const durable = await request("view").catch(() => null);
      if (!durable || (!durable.finished && durable.functional?.revision === payload.revision)) throw error;
      view = durable;
    }
    if (operation === "resume") paused = false;
    clock.reset(paused);
    render(view);
    if (operation === "submit") functionalDrafts.delete(functionalKey(view));
  });
}

function renderFunctional(view) {
  const region = element("functional");
  if (!region) return;
  region.replaceChildren();
  region.hidden = !isFunctionalActivity(view) || !view.item || Boolean(view.finished || view.feedback);
  if (region.hidden) return;
  const screen = view.functional;
  if (!screen || screen.paused || paused) return;
  const append = (tag, text, parent = region) => {
    const node = document.createElement(tag); node.textContent = text || ""; parent.append(node); return node;
  };
  const button = (id, label, action) => {
    const node = append("button", label); node.type = "button"; node.id = id;
    node.onclick = () => { if (!busy && !paused) action(); }; return node;
  };
  append("p", screen.consigne);
  if (screen.interruption_count) append("p", "Exercice interrompu. Reprends quand tu es prêt.");
  if (screen.phase === "messages") {
    append("p", `${screen.etape.titre} — ${screen.index + 1}/${screen.total}`);
    const message = append("p", screen.etape.texte); message.className = "document-source";
    button("functional-next", screen.index + 1 === screen.total ? "Restituer la consigne" : "Message suivant",
      () => functionalCommand("next"));
    return;
  }
  const key = functionalKey(view);
  const values = {...(functionalDrafts.get(key) || {})};
  const fields = screen.fields || [];
  for (const field of fields) {
    const label = append("label", ""); label.append(document.createTextNode(field.label));
    const input = document.createElement("input"); input.type = "text"; input.maxLength = 500;
    input.autocomplete = "off"; input.value = values[field.id] || ""; input.setAttribute("aria-label", field.label);
    input.oninput = () => {
      values[field.id] = input.value; functionalDrafts.set(key, values);
      validate.disabled = !fields.every(item => String(values[item.id] || "").trim());
    };
    label.append(input);
  }
  const validate = button("functional-submit", "Valider", () => functionalCommand("submit", values));
  validate.disabled = !fields.every(field => String(values[field.id] || "").trim());
}
