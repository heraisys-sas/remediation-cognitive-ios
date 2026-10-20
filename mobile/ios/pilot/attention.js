"use strict";

async function attentionCommand(operation, value) {
  const screen = state?.attention;
  if (!screen || !state?.item || (paused && operation !== "resume")) return;
  const payload = {session_id:state.session_id, item_id:state.item.id,
    revision:screen.revision, operation, elapsed_ms:Math.round(clock.elapsed())};
  if (operation === "select") payload.value = value;
  return perform(async () => {
    let view;
    try { view = await request("attention-step", payload); }
    catch (error) {
      const durable = await request("view").catch(() => null);
      if (!durable || (!durable.finished && !durable.feedback
          && durable.attention?.revision === payload.revision)) {
        render(durable || state); throw error;
      }
      view = durable;
    }
    if (operation === "resume") paused = false;
    else if (operation === "pause") paused = true;
    render(view); clock.reset(paused);
  });
}

function renderAttention(view) {
  const region = element("attention");
  if (!region) return;
  region.replaceChildren();
  region.hidden = !view?.attention || !view.item || Boolean(view.finished || view.feedback);
  if (region.hidden) return;
  const screen = view.attention;
  if (screen.paused || paused) return;
  const paragraph = (text, className = "") => {
    const node = document.createElement("p"); node.textContent = text || "";
    if (className) node.className = className;
    region.append(node); return node;
  };
  const button = (label, callback, primary = false) => {
    const node = document.createElement("button"); node.type = "button";
    node.className = primary ? "" : "secondaryButton";
    node.textContent = label;
    node.onclick = () => { if (!busy && !paused) callback(); };
    region.append(node); return node;
  };

  if (view.item.type === "reperer-essentiel") {
    paragraph(screen.instruction);
    const objective = document.createElement("section"); objective.className = "document-source";
    const goal = document.createElement("p"); goal.textContent = screen.objective;
    const criterion = document.createElement("p"); criterion.textContent = `À retenir : ${screen.criterion}`;
    objective.append(goal, criterion); region.append(objective);
    if (screen.phase === "messages") {
      paragraph(`Message ${screen.index + 1} sur ${screen.total}`);
      paragraph(screen.message?.text, "document-source");
      button("À prendre en compte", () => attentionCommand("select", "oui"));
      button("Sans conséquence selon les critères", () => attentionCommand("select", "non"));
    } else if (screen.phase === "submit") {
      paragraph("Tes choix sont conservés jusqu’à la correction finale.");
      for (const answer of screen.answers || []) {
        paragraph(`${answer.message} — ${answer.value === "oui" ? "À prendre en compte" : "Sans conséquence selon les critères"}`);
      }
      button("Vérifier mes choix", () => attentionCommand("submit"), true);
    }
    return;
  }

  if (screen.phase === "control") {
    const dossier = document.createElement("section"); dossier.className = "document-source";
    const heading = document.createElement("h2"); heading.textContent = screen.title;
    const goal = document.createElement("p"); goal.textContent = screen.goal;
    dossier.append(heading, goal); region.append(dossier);
    paragraph(`Point ${screen.position} sur ${screen.total} — ${screen.point.label}`);
    paragraph(screen.point.state, "document-source");
    screen.point.options.forEach(option => button(option, () => attentionCommand("select", option)));
  } else if (screen.phase === "interruption") {
    paragraph("Interruption"); paragraph(screen.instruction); paragraph(screen.prompt, "document-source");
    screen.options.forEach(option => button(option, () => attentionCommand("select", option)));
  } else if (screen.phase === "resume-choice") {
    paragraph("Retrouve le fil"); paragraph(screen.instruction);
    (screen.points || []).forEach(point => button(point.label, () => attentionCommand("select", point.id)));
  } else if (screen.phase === "submit") {
    const dossier = document.createElement("section"); dossier.className = "document-source";
    const heading = document.createElement("h2"); heading.textContent = screen.title;
    const goal = document.createElement("p"); goal.textContent = screen.goal;
    dossier.append(heading, goal); region.append(dossier);
    paragraph("Le contrôle est terminé.");
    for (const point of screen.point_summaries || []) {
      paragraph(`${point.label} : ${screen.points?.[point.id] === "valide" ? "Déjà validé" : "À reprendre"}`);
    }
    paragraph(`Point où reprendre : ${screen.resume_label || "choix enregistré"}`);
    paragraph("Le détour a reçu une réponse et ne compte pas dans le contrôle.");
    button("Valider le contrôle", () => attentionCommand("submit"), true);
  }
}
