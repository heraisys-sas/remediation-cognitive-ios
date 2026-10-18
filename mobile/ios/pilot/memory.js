"use strict";
let memoryTimer=null, memoryGeneration=0, failedMemoryTransition=null;
function stopMemoryTimer() {
  if(memoryTimer!==null) clearTimeout(memoryTimer);
  memoryTimer=null;
}
function renderMemoryFailure() {
  const region=element("memory"); region.replaceChildren();
  const text=document.createElement("p"); text.textContent="La présentation est masquée. Réessaie pour enregistrer le passage à la suite, ou termine la séance.";
  const retry=document.createElement("button"); retry.id="memory-retry"; retry.textContent="Réessayer";
  retry.onclick=()=>{ if(failedMemoryTransition) return memoryCommand("advance",null,failedMemoryTransition); };
  region.append(text,retry);
}
async function memoryCommand(operation,answer=null,retryPayload=null) {
  if(!state?.memory||(paused&&operation!=="resume")) return;
  const payload=retryPayload||{session_id:state.session_id,item_id:state.item.id,revision:state.memory.revision,
    operation,answer,elapsed_ms:Math.round(clock.elapsed())};
  return perform(async()=>{
    let view;
    try { view=await request("memory-step",payload); }
    catch(error) {
      const durable=await request("view").catch(()=>null);
      if(!durable || (!durable.finished&&durable.memory?.revision===payload.revision)) {
        if(operation==="advance") { failedMemoryTransition=payload; renderMemoryFailure(); }
        throw error;
      }
      view=durable;
    }
    failedMemoryTransition=null;
    if(operation==="resume") paused=false;
    clock.reset(paused); render(view);
    if(operation==="answer") element("answer").blur();
  });
}
function renderMemory(view) {
  stopMemoryTimer();
  const generation=++memoryGeneration;
  const region=element("memory"); region.replaceChildren();
  region.hidden=!view.memory||Boolean(view.feedback);
  const screen=view.memory;
  if(failedMemoryTransition && (failedMemoryTransition.session_id!==view.session_id || failedMemoryTransition.item_id!==view.item?.id || failedMemoryTransition.revision!==screen?.revision)) failedMemoryTransition=null;
  if(region.hidden||screen.paused||paused) return;
  if(failedMemoryTransition) { renderMemoryFailure(); return; }
  const paragraph=text=>{const p=document.createElement("p");p.textContent=text;region.append(p);return p;};
  const button=(text,operation)=>{
    const b=document.createElement("button");b.id=`memory-${operation}`;b.textContent=text;
    b.onclick=()=>memoryCommand(operation);region.append(b);
  };
  if(screen.interruptions) paragraph("Présentation interrompue : la reprise conserve l’étape enregistrée.");
  if(screen.phase==="pret") {
    paragraph(screen.instruction);button("Afficher","show");
  } else if(["element","liste","blanc"].includes(screen.phase)) {
    if(screen.phase==="element") {
      const p=paragraph(screen.content);p.className="memoryElement";
      paragraph(`${screen.position} sur ${screen.total}`);
    } else if(screen.phase==="liste") {
      const list=document.createElement("ul");
      for(const pair of screen.content) {const li=document.createElement("li");li.textContent=pair.join(" : ");list.append(li);}
      region.append(list);
    } else paragraph("…");
    button("Passer","skip");
    const valid=()=>generation===memoryGeneration&&!paused;
    memoryTimer=setTimeout(async()=>{
      // Masquer au terme prévu, avant d’attendre le transport ou sa sauvegarde.
      if(valid()) region.replaceChildren();
      while(busy&&valid()) await new Promise(resolve=>setTimeout(resolve,10));
      if(valid()) memoryCommand("advance");
    },Math.max(0,screen.remaining_ms-clock.elapsed()));
  } else if(screen.phase==="question") {
    paragraph(screen.question);
    element("answer").inputMode=screen.inputmode;
  }
}
