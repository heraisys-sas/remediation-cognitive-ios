"use strict";
const pqrstDrafts = new Map();
let pqrstDraftSession = null;
const pqrstDraftKey = view => JSON.stringify([view.session_id, view.item?.id, view.position, view.protocol?.phase]);
function clearPqrstDraft(view) { pqrstDrafts.delete(pqrstDraftKey(view)); }

function renderPqrstProtocol(view) {
  const zone = element("protocol");
  zone.replaceChildren();
  zone.hidden = !view.protocol;
  if (!view.protocol) return;
  if (pqrstDraftSession !== view.session_id) { pqrstDrafts.clear(); pqrstDraftSession = view.session_id; }
  const protocol = view.protocol;
  const append = (tag, text) => {
    const node = document.createElement(tag); node.textContent = text; zone.append(node); return node;
  };
  const button = (id, label, callback) => {
    const node = append("button", label); node.type = "button"; node.id = id;
    node.onclick = () => { if (!busy && !paused) return callback(); };
    return node;
  };
  protocol.paragraphs.forEach((text, index) => {
    const node = append(index ? "p" : "h3", text);
    if (!index) { node.id = "protocol-heading"; node.tabIndex = -1; }
  });
  if (protocol.paused) return;
  const draftKey = pqrstDraftKey(view);
  let value = pqrstDrafts.get(draftKey) ?? null, valid, reread, absentReread;
  const update = () => {
    const present = Boolean(value?.trim());
    if (valid) valid.disabled = !present;
    if (reread) reread.disabled = !present;
    if (absentReread) absentReread.hidden = present;
  };
  if (protocol.input_label) {
    const label = append("label", protocol.input_label);
    const field = document.createElement("textarea");
    field.id = "protocol-answer"; field.rows = 3; field.maxLength = 2000;
    field.value = value || "";
    label.htmlFor = field.id; zone.append(field);
    field.oninput = () => { value = field.value; pqrstDrafts.set(draftKey, value); update(); };
  } else if (protocol.options) {
    const choices = [];
    protocol.options.forEach((option, index) => {
      const node = button(`protocol-option-${index}`, option, () => {
        value = option;
        pqrstDrafts.set(draftKey, value);
        choices.forEach(choice => choice.setAttribute("aria-pressed", String(choice === node)));
        update();
      });
      node.className = "secondaryButton protocolChoice";
      node.setAttribute("aria-pressed", String(value === option)); choices.push(node);
    });
  }
  if (protocol.input_label || protocol.options) {
    valid = button("protocol-respond", protocol.response_label, () => protocolCommand("respond", value));
    button("protocol-absence", protocol.absence_label, () => protocolCommand("respond", null)).className = "secondaryButton";
    if (protocol.can_reread) {
      reread = button("protocol-reread", protocol.reread_label, () => protocolCommand("reread", value));
      reread.className = "secondaryButton";
      absentReread = button("protocol-reread-absence", protocol.reread_absence_label, () => protocolCommand("reread", null));
      absentReread.className = "secondaryButton";
    }
    update();
  }
  protocol.actions.forEach(action => button(`protocol-${action.operation}`, action.label, () => protocolCommand(action.operation)));
}

function pqrstFeedbackLines(result) {
  const detail = result.sequence || {}, observation = detail.observation;
  if (!observation) return [];
  const lines = ["Séquence terminée — résultats par étape", "Test après le résumé modèle, sans le rouvrir.",
    "La question formulée est conservée, sans score."];
  if (observation.reprise_apres_correction) lines.push("Reprise d’un texte déjà corrigé pendant cette séance.");
  lines.push(`Parcourir — sujet du texte : ${observation.statuts["1"] === "absence_declaree" ? "absence déclarée"
    : detail["1"]?.correcte ? "réponse exacte" : "réponse à revoir"}. Sujet proposé : ${detail["1"]?.attendue || ""}.`);
  lines.push(`Question formulée : ${observation.question || "absence déclarée"}`);
  const status = {absence_declaree:"absence déclarée", compatible:"idées reconnues", a_verifier:"à comparer au résumé",
    contradiction:"contradiction repérée", exacte:"réponse exacte", incorrecte:"réponse à revoir"};
  const condition = {sans_relecture:"sans relecture", apres_relecture:"après relecture", reprise_interrompue:"après interruption"};
  for (const [key, attempts] of Object.entries(observation.tentatives)) {
    attempts.forEach((attempt, index) => {
      const title = key === "4" ? "Reformulation" : `Test ${Number(key.slice(2)) + 1}`;
      lines.push(`${title} — ${index ? "tentative après aide" : "première réponse"} : ${status[attempt.correction.etat] || attempt.correction.etat} · ${condition[attempt.condition]}`);
      if (attempt.reponse !== null) lines.push(attempt.reponse);
    });
  }
  lines.push(`Résumé possible : ${detail["4"]?.modele || ""}`);
  (detail["5"]?.questions || []).forEach((answer, index) => lines.push(`Test ${index + 1} : ${answer}`));
  return lines;
}
