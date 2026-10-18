"use strict";
let contextesTimer = null;
let contextesImageGeneration = 0;
function stopContextesTimer() {
  if (contextesTimer !== null) clearTimeout(contextesTimer);
  contextesTimer = null;
}
async function contextesCommand(operation, value = null) {
  if (!state?.contextes || (paused && operation !== "resume")) return;
  const payload = {session_id:state.session_id,item_id:state.item.id,revision:state.contextes.revision,
    operation,value,elapsed_ms:Math.round(clock.elapsed())};
  return perform(async () => {
    let view;
    try { view = await request("contextes-step", payload); }
    catch (error) {
      const durable = await request("view").catch(() => null);
      if (!durable) throw error;
      if (!durable.finished && durable.contextes?.revision === payload.revision) throw error;
      view = durable;
    }
    if (operation === "resume") paused = false;
    clock.reset(paused); render(view);
  });
}
function renderContextes(view) {
  stopContextesTimer();
  const generation = ++contextesImageGeneration;
  const region = element("contextes");
  region.replaceChildren();
  region.hidden = !view.contextes;
  const screen = view.contextes;
  if (!screen || screen.paused || paused) return;
  const paragraph = text => { const p=document.createElement("p"); p.textContent=text; region.append(p); };
  const button = (label, operation, value=null) => {
    const node=document.createElement("button"); node.textContent=label;
    node.id=`contextes-${operation}${operation === "answer" ? "-" + (screen.options || []).indexOf(value) : ""}`;
    node.onclick=()=>contextesCommand(operation,value); region.append(node); return node;
  };
  paragraph(`${screen.pass === "decouverte" ? "Découverte après photo" : "Rappel sans photo"} · ${view.position} sur ${view.total}`);
  if (screen.image_failed) paragraph("La scène n’a pas pu être chargée. Tu peux réessayer ou terminer la séance.");
  if (screen.phase === "pret") { paragraph(screen.instruction); button(screen.image_failed ? "Réessayer" : "Afficher", "show"); }
  if (screen.question) paragraph(screen.question);
  if (screen.image) {
    const image=document.createElement("img");
    image.width=screen.image.width; image.height=screen.image.height; image.alt=screen.image.alt;
    image.srcset=screen.image.srcset; image.src=screen.image.src;
    const figure=document.createElement("figure");
    const caption=document.createElement("figcaption"); caption.textContent=screen.image.alt;
    caption.setAttribute("aria-hidden","true");
    figure.append(image,caption); region.append(figure);
    const valid=()=>generation===contextesImageGeneration && !paused;
    const dispatch=async operation=>{
      while (busy && valid()) await new Promise(resolve=>setTimeout(resolve,10));
      if (valid()) return contextesCommand(operation);
    };
    let settled=false;
    const loaded=async()=>{
      if (settled || !valid()) return;
      try { if (image.decode) await image.decode(); } catch { return failed(); }
      if (!valid()) return;
      settled=true; stopContextesTimer();
      if (screen.phase === "photo") return dispatch("loaded");
      if (screen.phase === "exposition") {
        contextesTimer=setTimeout(()=>{ if(valid()) dispatch("hide"); },Math.max(0,screen.remaining_ms-clock.elapsed()));
        button("Passer", "hide");
      } else if (screen.phase === "feedback") {
        if (!screen.reveal_recorded) await dispatch("reveal-loaded");
      }
    };
    const failed=()=>{
      if (settled || !valid()) return;
      settled=true; stopContextesTimer();
      image.hidden=true; caption.textContent="La scène n’a pas pu être chargée. Tu peux réessayer ou terminer la séance.";
      dispatch("image-error");
    };
    image.onload=loaded; image.onerror=failed;
    contextesTimer=setTimeout(failed,15000);
    if (image.complete && image.naturalWidth) loaded();
  }
  for (const option of screen.options || []) {
    const choice=button(option,"answer",option); choice.className="protocolChoice";
  }
  if (screen.phase === "feedback") button(screen.pass === "decouverte" && view.position === view.total ? "Passer au rappel" : "Continuer", "next");
}
