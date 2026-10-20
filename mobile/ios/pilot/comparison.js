"use strict";

const comparisonDrafts = new Map();

function comparisonDraftKey(view) {
  return JSON.stringify([view?.session_id, view?.item?.id, view?.position]);
}

function renderComparison(view) {
  const region = element("comparison");
  if (!region) return;
  region.replaceChildren();
  region.hidden = view?.activity !== "comparer-documents" || !view?.item || Boolean(view?.finished);
  if (region.hidden) return;

  const screen = view.comparison;
  if (!screen || screen.paused || view.feedback) return;
  if (!Array.isArray(screen.documents) || !Array.isArray(screen.champs)) return;

  const instruction = view.item.contenu?.consigne;
  if (instruction) {
    const paragraph = document.createElement("p");
    paragraph.textContent = instruction;
    region.append(paragraph);
  }

  const supports = document.createElement("div");
  supports.className = "comparison-documents";
  supports.setAttribute("aria-label", "Documents à comparer");
  screen.documents.forEach((documentData, documentIndex) => {
    const article = document.createElement("article");
    article.className = "comparison-document";
    const heading = document.createElement("h2");
    heading.textContent = documentData?.titre ?? `Document ${documentIndex + 1}`;
    article.append(heading);
    const lines = document.createElement("ul");
    (Array.isArray(documentData?.lignes) ? documentData.lignes : []).forEach(line => {
      const row = document.createElement("li");
      const label = document.createElement("strong");
      label.textContent = line?.label ?? "";
      const text = document.createElement("span");
      text.textContent = line?.texte ?? "";
      row.append(label, document.createTextNode(": "), text);
      lines.append(row);
    });
    article.append(lines);
    supports.append(article);
  });
  region.append(supports);

  const key = comparisonDraftKey(view);
  const draft = comparisonDrafts.get(key) || {};
  const fields = document.createElement("div");
  fields.className = "comparison-fields";
  const radios = [];
  screen.champs.forEach((field, fieldIndex) => {
    const fieldset = document.createElement("fieldset");
    fieldset.className = "comparison-field";
    const legend = document.createElement("legend");
    legend.textContent = field?.label ?? `Élément ${fieldIndex + 1}`;
    fieldset.append(legend);
    [["conforme", "Conforme"], ["ecart", "Écart"]].forEach(([value, labelText]) => {
      const label = document.createElement("label");
      label.className = "comparison-option";
      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = `comparison-${key}-${field?.id ?? fieldIndex}`;
      radio.value = value;
      radio.checked = draft[field?.id] === value;
      radio.setAttribute("aria-label", `${legend.textContent} : ${labelText}`);
      radio.addEventListener("change", () => {
        if (radio.checked) {
          draft[field.id] = value;
          comparisonDrafts.set(key, draft);
          updateSubmit();
        }
      });
      radios.push(radio);
      label.append(radio, document.createTextNode(` ${labelText}`));
      fieldset.append(label);
    });
    fields.append(fieldset);
  });
  region.append(fields);

  const submit = document.createElement("button");
  submit.type = "button";
  submit.textContent = "Valider";
  submit.className = "comparison-submit";
  const exactDraft = () => Object.keys(draft).length === screen.champs.length
    && screen.champs.every(field => Object.prototype.hasOwnProperty.call(draft, field.id)
      && (draft[field.id] === "conforme" || draft[field.id] === "ecart"));
  const updateSubmit = () => { submit.disabled = Boolean(paused || !exactDraft()); };
  updateSubmit();
  submit.addEventListener("click", () => {
    if (busy || paused || submit.disabled) return;
    const answer = {};
    screen.champs.forEach(field => { answer[field.id] = draft[field.id]; });
    comparisonCommand("answer", answer);
  });
  region.append(submit);
}

async function comparisonCommand(operation, answer = null) {
  if (!state?.comparison || !state?.item) return;
  if (paused && operation === "answer") return;
  if (paused && operation === "pause" && state.comparison.paused) return;
  const payload = {
    session_id: state.session_id,
    item_id: state.item.id,
    revision: state.comparison.revision,
    operation,
    elapsed_ms: Math.round(clock.elapsed()),
  };
  if (operation === "answer") payload.answer = answer;
  const previousView = state;
  return perform(async () => {
    let view;
    try {
      view = await request("comparison-step", payload);
    } catch (error) {
      const durable = await request("view").catch(() => null);
      if (!durable) throw error;
      const sameStep = !durable.finished
        && durable.session_id === payload.session_id
        && durable.item?.id === payload.item_id
        && durable.comparison?.revision === payload.revision;
      if (sameStep) {
        render(durable);
        throw error;
      }
      view = durable;
    }
    if (operation === "resume") paused = false;
    if (view.comparison?.paused) paused = true;
    else if (operation === "resume" || operation === "answer") paused = false;
    if (operation === "answer" && (view.feedback || view.finished)) {
      comparisonDrafts.delete(comparisonDraftKey(previousView));
    }
    render(view);
    clock.reset(paused);
  });
}
