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
    if(screen.audio_failed)paragraph("Lecture interrompue. Tu peux reprendre la série depuis le début.");
    paragraph(screen.instruction);button(screen.audio_failed?"Réécouter depuis le début":"Afficher","show");
  } else if(["element","liste","blanc","attente"].includes(screen.phase)) {
    if(screen.phase==="element") {
      const p=paragraph(screen.content);p.className="memoryElement";
      paragraph(`${screen.position} sur ${screen.total}`);
    } else if(screen.phase==="liste") {
      const list=document.createElement("ul");
      for(const pair of screen.content) {const li=document.createElement("li");li.textContent=Array.isArray(pair)?pair.join(" : "):pair;list.append(li);}
      region.append(list);
    } else paragraph(screen.phase==="attente"?"Attente avant le rappel…":"…");
    button("Passer","skip");
    const valid=()=>generation===memoryGeneration&&!paused;
    memoryTimer=setTimeout(async()=>{
      // Masquer au terme prévu, avant d’attendre le transport ou sa sauvegarde.
      if(valid()) region.replaceChildren();
      while(busy&&valid()) await new Promise(resolve=>setTimeout(resolve,10));
      if(valid()) memoryCommand("advance");
    },Math.max(0,screen.remaining_ms-clock.elapsed()));
  } else if(screen.phase==="audio") {
    paragraph(`Écoute… Série ${screen.group} sur ${screen.groups}`);
    const token=`memory-audio-${view.session_id}-${screen.revision}`;
    memoryAudio={token,revision:screen.revision,session:view.session_id};
    memoryAudio.timeout=setTimeout(()=>memoryNativeSpeechEvent({kind:"speech",token,status:"failed"}),15000);
    speechRequest("play-audio",{token,path:screen.audio_path}).catch(()=>memoryNativeSpeechEvent({kind:"speech",token,status:"failed"}));
  } else if(screen.phase==="question") {
    paragraph(screen.question);
    element("answer").inputMode=screen.inputmode;
    for(const [index,option] of (screen.options||[]).entries()){
      const choice=document.createElement("button");choice.id=`memory-choice-${index}`;choice.className="protocolChoice";choice.textContent=option;choice.onclick=()=>memoryCommand("answer",option);region.append(choice);
    }
  }
}

let memoryAudio=null;
async function memoryNativeSpeechEvent(event){
  if(!memoryAudio||event.kind!=='speech'||event.token!==memoryAudio.token)return false;
  if(!['finished','stopped','failed'].includes(event.status))return true;
  const audio=memoryAudio;memoryAudio=null;clearTimeout(audio.timeout);
  while(busy&&!paused&&state?.memory?.revision===audio.revision)await new Promise(resolve=>setTimeout(resolve,10));
  if(!paused&&state?.memory?.revision===audio.revision&&state?.session_id===audio.session)
    await memoryCommand(event.status==='finished'?'advance':'audio-error');
  return true;
}
function stopMemoryAudio(){if(memoryAudio){clearTimeout(memoryAudio.timeout);memoryAudio=null;speechRequest('cancel').catch(()=>{});}}
