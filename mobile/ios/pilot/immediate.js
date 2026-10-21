"use strict";
// Le runtime racine fournit element(), request(), perform(), state, paused, clock.
let immediateView = null, immediateTimer = null, immediateTimerResolve = null, immediateGeneration = 0;
let immediateSpeechToken = null, immediateSpeechResolve = null, immediateSpeechWatchdog = null, immediateSpeechKey = null;

function immediateStopTimer() {
  if (immediateTimer !== null) clearTimeout(immediateTimer);
  immediateTimer = null;
  const resolve = immediateTimerResolve; immediateTimerResolve = null; resolve?.();
  immediateGeneration++;
}
function immediateNode(tag, text, cls) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = String(text);
  if (cls) node.className = cls;
  return node;
}
function immediateButton(label, callback, primary = false) {
  const node = immediateNode("button", label, primary ? "" : "secondaryButton");
  node.type = "button"; node.addEventListener("click", callback); return node;
}
function immediateRegion() { return element("immediate"); }
function immediateWait(ms, generation) {
  return new Promise(resolve => {
    if (generation !== immediateGeneration) { resolve(); return; }
    immediateTimerResolve = resolve;
    immediateTimer = setTimeout(() => { immediateTimer = null; immediateTimerResolve = null; resolve(); }, Math.max(0, ms));
  });
}
function immediateSequencePlan(values, signalMs, intervalMs) {
  return values.flatMap((value,index)=>[{phase:"element",value,duration_ms:signalMs},...(index<values.length-1?[{phase:"blanc",duration_ms:intervalMs}]:[])]);
}
function immediatePositionLabel(position) {
  return `${position.y<.34?"En haut":position.y>.66?"En bas":"Au milieu"}, ${position.x<.34?"à gauche":position.x>.66?"à droite":"au centre"}`;
}
function immediateAudioUnavailable(message) {
  const region=immediateRegion();if(!region)return;
  region.replaceChildren(immediateNode("p",message),immediateButton("Réessayer la lecture",()=>{immediateSpeechKey=null;renderImmediate(immediateView);},true));
}
function immediateVisualGlyph(kind,color="currentColor") {
  const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.setAttribute("viewBox","0 0 80 80");svg.setAttribute("aria-hidden","true");svg.setAttribute("focusable","false");
  const paths={triangle:"M40 8L73 69H7Z",carre:"M12 12H68V68H12Z",losange:"M40 5L75 40L40 75L5 40Z",etoile:"M40 5L49 29L75 30L54 46L62 72L40 57L18 72L26 46L5 30L31 29Z",croix:"M29 8H51V29H72V51H51V72H29V51H8V29H29Z",pomme:"M40 22Q17 8 11 34Q5 65 29 70Q40 75 50 70Q76 65 70 34Q64 8 40 22Z M40 22Q38 5 52 7L54 15Q44 15 40 22Z",cle:"M29 13A17 17 0 1 0 29 47L41 59H50V68H60V58L43 41A17 17 0 0 0 29 13Z M23 23A6 6 0 1 1 23 35A6 6 0 0 1 23 23Z",tasse:"M13 18H53V27H62Q75 27 75 41Q75 55 53 55Q50 67 33 67Q13 67 13 47Z M53 34V48Q67 48 67 41Q67 34 53 34Z",livre:"M9 15Q25 8 40 19Q55 8 71 15V65Q55 58 40 69Q25 58 9 65Z M40 19V69"};
  const path=paths[kind],shape=document.createElementNS("http://www.w3.org/2000/svg",path?"path":"circle");if(path)shape.setAttribute("d",path);else{shape.setAttribute("cx","40");shape.setAttribute("cy","40");shape.setAttribute("r","29");}shape.setAttribute("fill",color);shape.setAttribute("fill-rule","evenodd");svg.append(shape);return svg;
}
function immediateBoard(positions,className="mi-object-board") {
  const board=immediateNode("div","",`mi-visual-board ${className}`);board.style.setProperty("--mi-object-count",positions.length);
  const cells=positions.map((p,i)=>{const cell=immediateNode("div","","mi-object-slot");cell.style.left=`${p.x*100}%`;cell.style.top=`${p.y*100}%`;cell.setAttribute("aria-label",`Emplacement ${i+1}`);board.append(cell);return cell;});
  return {board,cells};
}


function immediatePathLinks(area) {
  const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
  svg.setAttribute("viewBox","0 0 100 100");svg.setAttribute("preserveAspectRatio","none");
  svg.setAttribute("aria-hidden","true");svg.classList.add("immediate-path-links");area.append(svg);return svg;
}
function immediateDrawPath(svg,positions,path) {
  svg.replaceChildren();
  for(let i=1;i<path.length;i++){
    const from=positions.find(p=>p.id===path[i-1]),to=positions.find(p=>p.id===path[i]);
    if(!from||!to)continue;
    const line=document.createElementNS("http://www.w3.org/2000/svg","line");
    line.setAttribute("x1",from.x*100);line.setAttribute("y1",from.y*100);
    line.setAttribute("x2",to.x*100);line.setAttribute("y2",to.y*100);
    line.setAttribute("vector-effect","non-scaling-stroke");svg.append(line);
  }
}
function immediatePathTouch(board,cells,positions,selected,limit,redraw) {
  let gesture=null,suppressClick=false;
  const hit=(x,y)=>cells.findIndex(cell=>{const r=cell.getBoundingClientRect();return x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom;});
  const add=index=>{if(index<0||selected.length>=limit||selected.includes(positions[index].id))return;selected.push(positions[index].id);redraw();};
  const toggle=index=>{if(index<0)return;const id=positions[index].id,existing=selected.indexOf(id);if(existing>=0)selected.splice(existing,1);else if(selected.length<limit)selected.push(id);redraw();};
  board.addEventListener("pointerdown",event=>{
    if(busy||paused||event.isPrimary===false||event.button!==0||gesture)return;
    const first=hit(event.clientX,event.clientY);if(first<0)return;
    gesture={id:event.pointerId,first,x:event.clientX,y:event.clientY,dragging:false};suppressClick=true;
    if(event.isTrusted)board.setPointerCapture?.(event.pointerId);event.preventDefault();
  });
  const move=event=>{
    if(!gesture||gesture.id!==event.pointerId||busy||paused)return;
    const steps=Math.max(1,Math.ceil(Math.hypot(event.clientX-gesture.x,event.clientY-gesture.y)/8));
    const x=gesture.x,y=gesture.y;
    for(let step=1;step<=steps;step++){
      const index=hit(x+(event.clientX-x)*step/steps,y+(event.clientY-y)*step/steps);
      if(index>=0&&index!==gesture.first&&!gesture.dragging){gesture.dragging=true;add(gesture.first);}
      if(gesture.dragging)add(index);
    }
    gesture.x=event.clientX;gesture.y=event.clientY;
  };
  board.addEventListener("pointermove",event=>{if(gesture?.id!==event.pointerId)return;move(event);event.preventDefault();});
  const end=(event,cancelled)=>{
    if(!gesture||gesture.id!==event.pointerId)return;
    if(!cancelled&&!busy&&!paused){move(event);if(!gesture.dragging)toggle(gesture.first);}
    gesture=null;
    if(board.hasPointerCapture?.(event.pointerId))board.releasePointerCapture(event.pointerId);
  };
  board.addEventListener("pointerup",event=>end(event,false));
  board.addEventListener("pointercancel",event=>end(event,true));
  board.addEventListener("lostpointercapture",()=>{gesture=null;});
  cells.forEach((cell,index)=>cell.onclick=event=>{
    // Le clic synthétisé après un geste ne doit pas retirer la dernière case.
    if(event?.detail>0&&suppressClick){suppressClick=false;return;}
    if(!busy&&!paused)toggle(index);
  });
}

async function immediateCommand(operation, extra = {}) {
  if (!immediateView || !immediateView.immediate || busy) return;
  immediateStopTimer();
  const view = immediateView, screen = view.immediate;
  const payload = {session_id:view.session_id, item_id:view.item_id, revision:screen.revision,
    operation, elapsed_ms:Math.round(clock.elapsed()), ...extra};
  if (operation === "answer") payload.assisted = Boolean(screen.assisted);
  await perform(async () => {
    let next;
    try { next = await request("immediate-step", payload); }
    catch (error) {
      const durable = await request("view").catch(() => null);
      if (!durable || durable.immediate?.revision === payload.revision) throw error;
      next = durable;
    }
    clock.reset(false); render(next);
  });
}
function immediateSchedule(ms, operation, generation) {
  immediateTimer = setTimeout(async () => {
    if (generation !== immediateGeneration || !immediateView || paused) return;
    while (busy && generation === immediateGeneration && !paused) await new Promise(resolve => setTimeout(resolve, 15));
    if (generation === immediateGeneration && immediateView && !paused) immediateCommand(operation);
  }, Math.max(0, ms));
}
function immediateTimerCommand(operation, generation = immediateGeneration) {
  while (busy && generation === immediateGeneration && !paused) {
    return setTimeout(() => immediateTimerCommand(operation, generation), 15);
  }
  if (generation === immediateGeneration && immediateView && !paused) immediateCommand(operation);
}

async function immediateVisualStimulus(screen, region, generation = immediateGeneration) {
  const s = screen.stimulus || {};
  const activity = screen.kind || "";
  if (activity === "code") {
    const chars = s.chiffres || [];
    const output = immediateNode("div", "", "mi-code"); region.append(output);
    const plan = immediateSequencePlan(chars, screen.params?.signal_ms || 1500, screen.params?.intervalle_ms || 500);
    for (const event of plan) {
      if (generation !== immediateGeneration || paused) return true;
      output.textContent = event.phase === "element" ? event.value : "";
      await immediateWait(event.duration_ms, generation);
    }
    output.replaceChildren();
    if (generation === immediateGeneration) immediateTimerCommand(screen.example ? "example-end" : "exposure-ended", generation);
    return true;
  }
  if (activity === "chemin") {
    const area = immediateNode("div", "", "immediate-path"); region.append(area);
    const positions = s.positions || [], path = s.trajet || [], cells = new Map();
    positions.forEach(position => {
      const cell = immediateNode("div", "", "immediate-path-cell");
      cell.style.left = `${position.x * 100}%`; cell.style.top = `${position.y * 100}%`;
      cell.setAttribute("aria-hidden", "true"); cells.set(position.id, cell); area.append(cell);
    });
    for (let index = 0; index < path.length; index++) {
      if (generation !== immediateGeneration || paused) return true;
      cells.get(path[index])?.classList.add("is-lit");
      await immediateWait(screen.params?.signal_ms || 1500, generation);
      cells.get(path[index])?.classList.remove("is-lit");
      if (index < path.length - 1) await immediateWait(screen.params?.intervalle_ms || 500, generation);
    }
    if (generation === immediateGeneration) immediateTimerCommand(screen.example ? "example-end" : "exposure-ended", generation);
    return true;
  }
  if (activity === "changement") {
    const items = s.avant || [], condition = screen.params?.condition;
    const {board,cells} = immediateBoard(items.map(item => ({x:(Number(item.position)+.5)/items.length,y:.5})));
    region.append(board);
    items.forEach((item,index) => cells[index].append(immediateVisualGlyph(condition === "couleur" ? "cercle" : item.forme,
      condition === "forme" ? "#8a8a8a" : s.palette?.[item.couleur] || "currentColor")));
    immediateTimer=setTimeout(()=>{board.replaceChildren();immediateTimerCommand(screen.example?"example-end":"exposure-ended",generation);}, screen.params?.exposition_ms||5000);
    return true;
  }
  if (activity === "objets") {
    const {board,cells}=immediateBoard(s.positions||[]);region.append(board);
    for(const object of s.objets||[]){const index=(s.positions||[]).findIndex(position=>position.id===s.modele?.[object.id]);if(index>=0)cells[index].append(immediateVisualGlyph(object.id));}
    immediateTimer=setTimeout(()=>{board.replaceChildren();immediateTimerCommand(screen.example?"example-end":"exposure-ended",generation);}, screen.params?.exposition_ms||6000);
    return true;
  }
  return false;
}

function immediateResponse(screen, region) {
  const kind=screen.kind || "";
  const prompt=immediateNode("p", screen.question || "Réponds à ton rythme."); region.append(prompt);
  if(kind==="code") {
    const input=document.createElement("input"),actions=immediateNode("div","","mi-controls"),status=immediateNode("p","");
    input.inputMode="numeric";input.autocomplete="off";input.maxLength=32;input.setAttribute("aria-label","Le code, dans le même ordre.");region.append(input,status,actions);
    const submit=()=>{const code=input.value.replace(/[\s-]/g,"");
      if(!/^[0-9]*$/.test(code)){status.textContent="Utilise uniquement des chiffres.";input.focus();return;}
      if(code.length!==screen.params.longueur){status.textContent=code.length?"Le code est incomplet ou sa longueur est différente.":"La saisie est vide.";
        actions.replaceChildren(immediateButton("Corriger",()=>{actions.replaceChildren(immediateButton("Valider le code",submit,true));input.focus();}),
          immediateButton("Confirmer cette réponse",()=>immediateCommand("answer",{response:code||null,observations:code?{}:{absence_declaree:true}}),true));
      } else immediateCommand("answer",{response:code,observations:{}});
    };
    actions.append(immediateButton("Valider le code",submit,true));input.focus();
  } else if(kind==="chemin") {
    const positions=screen.stimulus?.positions||[],selected=[],{board,cells}=immediateBoard(positions,"immediate-path");
    const svg=immediatePathLinks(board);board.classList.add("immediate-path-input");region.append(board);
    const status=immediateNode("p","","indice"),confirmation=immediateNode("div","","mi-controls");
    const redraw=()=>{cells.forEach((cell,index)=>{const id=positions[index].id;const rank=selected.flatMap((value,i)=>value===id?[i+1]:[]);cell.replaceChildren(immediateNode("span",rank.join(" · "),"immediate-path-rank"));cell.setAttribute("aria-pressed",String(rank.length>0));cell.setAttribute("aria-label",`${immediatePositionLabel(positions[index])}${rank.length?`; votre choix ${rank.join(", ")}`:""}`);});
      immediateDrawPath(svg,positions,selected);status.textContent=`${selected.length} choix sur ${screen.params.longueur}.`;clear.disabled=!selected.length;confirmation.replaceChildren();};
    positions.forEach((position,index)=>{const cell=immediateNode("button","","secondaryButton");cell.type="button";cell.classList.add("immediate-path-cell");cell.style.left=`${position.x*100}%`;cell.style.top=`${position.y*100}%`;cell.setAttribute("aria-label",immediatePositionLabel(position));cell.addEventListener("keydown",event=>{const d={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];if(!d)return;event.preventDefault();const options=positions.map((p,i)=>({p,i,dx:p.x-position.x,dy:p.y-position.y})).filter(v=>v.dx*d[0]+v.dy*d[1]>0).sort((a,b)=>(a.dx*a.dx+a.dy*a.dy)-(b.dx*b.dx+b.dy*b.dy));if(options.length)cells[options[0].i].focus();});cells[index].replaceWith(cell);cells[index]=cell;});
    const clear=immediateButton("Vider les cases",()=>{selected.length=0;redraw();});
    const submit=()=>{if(selected.length<screen.params.longueur){confirmation.replaceChildren(immediateNode("p","Le chemin est incomplet."),immediateButton("Corriger",()=>confirmation.replaceChildren()),immediateButton("Confirmer cette réponse",()=>immediateCommand("answer",{response:[...selected],observations:{}}),true));}else immediateCommand("answer",{response:[...selected],observations:{}});};
    region.append(status,immediateNode("p","Relie les cases avec le doigt, ou touche-les une à une dans l’ordre. Tu peux laisser le chemin incomplet.","indice"),clear,immediateButton("Valider le chemin",submit,true),confirmation);immediatePathTouch(board,cells,positions,selected,screen.params.longueur,redraw);redraw();cells[0]?.focus();
  } else if(kind==="changement") {
    const selected=new Set(),items=screen.stimulus?.apres||[],condition=screen.params?.condition;
    const {board,cells}=immediateBoard(items.map(item=>({x:(Number(item.position)+.5)/items.length,y:.5})));region.append(board);
    items.forEach((item,index)=>{const cell=immediateButton("",()=>{const limit=condition==="association"?2:1;if(selected.has(item.position))selected.delete(item.position);else if(selected.size<limit)selected.add(item.position);cell.setAttribute("aria-pressed",String(selected.has(item.position)));});cell.classList.add("mi-visual-cell");cell.setAttribute("aria-label",`Élément ${index+1}`);cell.setAttribute("aria-pressed","false");cell.append(immediateVisualGlyph(condition==="couleur"?"cercle":item.forme,condition==="forme"?"#8a8a8a":screen.stimulus?.palette?.[item.couleur]||"currentColor"));cells[index].replaceWith(cell);cells[index]=cell;});
    region.append(immediateButton("Identique",()=>immediateCommand("answer",{response:{decision:"identique",localisation:[]},observations:{}})));
    region.append(immediateButton("Différent",()=>immediateCommand("answer",{response:{decision:"different",localisation:[...selected],localisation_absente:!selected.size},observations:{}}),true));
  } else if(kind==="objets") {
    const response={},s=screen.stimulus||{},positions=s.positions||[],objects=s.objets||[],workspace=immediateNode("div"),reserve=immediateNode("div","","mi-object-reserve"),controls=immediateNode("div","","mi-controls");let selected=null;
    region.append(workspace,reserve,controls);
    const redraw=()=>{workspace.replaceChildren();reserve.replaceChildren();controls.replaceChildren();const {board,cells}=immediateBoard(positions);
      positions.forEach((position,index)=>{const occupant=Object.keys(response).find(id=>response[id]===position.id);const cell=immediateButton("",()=>{if(occupant){delete response[occupant];selected=null;redraw();return;}if(selected){response[selected]=position.id;selected=null;redraw();}});cell.classList.add("mi-object-slot");cell.style.left=`${position.x*100}%`;cell.style.top=`${position.y*100}%`;cell.setAttribute("aria-label",`Emplacement ${index+1}${occupant?` : ${objects.find(o=>o.id===occupant)?.nom||occupant}`:" : vide"}`);if(occupant)cell.append(immediateVisualGlyph(occupant));cells[index].replaceWith(cell);});
      workspace.append(board,immediateNode("p",selected?"Choisissez un emplacement.":"Choisissez un objet, puis son emplacement."));
      for(const id of s.reserve||[]){const object=objects.find(o=>o.id===id),button=immediateButton(object?.nom||id,()=>{selected=selected===id?null:id;redraw();});button.disabled=Boolean(response[id]);button.setAttribute("aria-pressed",String(selected===id));button.append(immediateVisualGlyph(id));reserve.append(button);}
      const clear=immediateButton("Vider les cases",()=>{Object.keys(response).forEach(id=>delete response[id]);selected=null;redraw();});clear.disabled=!Object.keys(response).length;controls.append(clear,immediateButton("Valider les placements",()=>{if(Object.keys(response).length<objects.length){controls.replaceChildren(immediateNode("p","Un emplacement est vide."),immediateButton("Corriger",redraw),immediateButton("Confirmer cette réponse",()=>immediateCommand("answer",{response:{...response},observations:{}}),true));}else immediateCommand("answer",{response:{...response},observations:{}});},true));
    };redraw();
  }
}

function immediateRenderModel(screen, root, response = null) {
  const kind=screen.kind,s=screen.model||{},params=screen.params||{};
  if(kind==="code"){root.append(immediateNode("p",`Code présenté : ${(s.chiffres||[]).join(" ")}`));return;}
  if(kind==="chemin"){
    const area=immediateNode("div","","immediate-path immediate-path-model");
    for(const position of s.positions||[]){const rank=(s.trajet||[]).flatMap((id,index)=>id===position.id?[index+1]:[]);const cell=immediateNode("div","","immediate-path-cell");cell.append(immediateNode("span",rank.join(" · "),"immediate-path-rank"));cell.style.left=`${position.x*100}%`;cell.style.top=`${position.y*100}%`;cell.setAttribute("aria-label",immediatePositionLabel(position)+(rank.length?`, choix ${rank.join(", ")}`:""));area.append(cell);}
    immediateDrawPath(immediatePathLinks(area),s.positions||[],s.trajet||[]);
    root.append(immediateNode("p","Le chemin présenté, avec son ordre :"),area);return;
  }
  if(kind==="changement"){
    const comparison=immediateNode("div","","mi-model-comparison");root.append(comparison);
    for(const [label,key] of [["Avant","avant"],["Après","apres"]]){const items=s[key]||[],condition=params.condition,{board,cells}=immediateBoard(items.map(item=>({x:(Number(item.position)+.5)/items.length,y:.5})));items.forEach((item,index)=>cells[index].append(immediateVisualGlyph(condition==="couleur"?"cercle":item.forme,condition==="forme"?"#8a8a8a":s.palette?.[item.couleur]||"currentColor")));const group=immediateNode("section");group.append(immediateNode("h4",label),board);comparison.append(group);}
    const correction=screen.correction;if(correction?.positions_modifiees?.length){const text=params.condition==="association"?"Deux formes ont échangé leurs couleurs.":params.condition==="couleur"?"Une couleur a changé.":"Une forme a changé.";root.append(immediateNode("p",text));}
    return;
  }
  if(kind==="objets"){
    const comparison=immediateNode("div","","mi-model-comparison");root.append(comparison);
    for(const [label,placements] of [["Modèle",s.modele||{}],["Ta réponse",response||{}]]){const {board,cells}=immediateBoard(s.positions||[]);for(const object of s.objets||[]){const index=(s.positions||[]).findIndex(position=>position.id===placements[object.id]);if(index>=0)cells[index].append(immediateVisualGlyph(object.id));}const group=immediateNode("section");group.append(immediateNode("h4",label),board);comparison.append(group);}
  }
}
function immediateRenderFeedback(screen,region){
  const c=screen.correction||{},record=screen.help_response||screen.first_response||{};
  region.append(immediateNode("p",c.exacte===true?"Réponse exacte.":c.exacte===false?"Compare ta réponse au modèle.":"Absence de réponse déclarée."));
  if(c.positions_exactes!=null)region.append(immediateNode("p",`${c.positions_exactes} positions exactes sur ${c.longueur} ; ${c.elements_retrouves} éléments retrouvés, indépendamment de l’ordre.`));
  if(c.associations_exactes!=null)region.append(immediateNode("p",`${c.associations_exactes} association${c.associations_exactes>1?"s":""} exacte${c.associations_exactes>1?"s":""} sur ${c.nombre} ; ${c.associations_erronees} placement${c.associations_erronees>1?"s":""} différent${c.associations_erronees>1?"s":""} ; ${c.non_places} objet${c.non_places>1?"s":""} non placé${c.non_places>1?"s":""}.`));
  if(c.type){const labels={detection:"Changement détecté",changement_manque:"Changement non détecté",fausse_alerte:"Différence déclarée sur des compositions identiques",rejet_correct:"Compositions identiques reconnues"};region.append(immediateNode("p",labels[c.type]||"Réponse enregistrée."));if(c.localisation_exacte!=null)region.append(immediateNode("p",c.localisation_exacte?"Localisation exacte.":"Localisation différente du modèle."));}
  immediateRenderModel(screen,region,record.response);
  if(screen.assisted)region.append(immediateNode("p","Essai après réexposition et correction. La première réponse est conservée."));
}

function renderImmediate(view) {
  immediateStopTimer(); immediateView=view;
  const region=immediateRegion(); if(!region)return;
  region.replaceChildren(); region.hidden=!view?.immediate;
  if(!view?.immediate)return;
  const screen=view.immediate;
  if(screen.interruptions) region.append(immediateNode("p","Présentation interrompue. La reprise conserve l’étape enregistrée."));
  if(screen.phase==="pret") {
    region.append(immediateNode("p",screen.instruction||"Prends le temps de lire la consigne."));
    if(screen.index===1&&!screen.assisted&&!screen.example)region.append(immediateButton("Voir un exemple",()=>immediateCommand("example")));
    region.append(immediateButton("Commencer",()=>immediateCommand("show"),true));
  } else if(screen.phase==="exposition") {
    if(screen.modalite==="auditive") {
      region.append(immediateNode("p","Écoute chaque chiffre une fois."));
      immediateSpeakCurrentDigit(screen);
    } else if(!immediateVisualStimulus(screen,region)) region.append(immediateNode("p","Présentation en cours…"));
  } else if(screen.phase==="exemple") {
    if(screen.example_stage==="exposition") {
      if(screen.modalite==="auditive") {region.append(immediateNode("p","Écoute cet exemple."));immediateSpeakCurrentDigit(screen);}
      else immediateVisualStimulus(screen,region);
    } else {
      region.append(immediateNode("p","Voici le modèle de l’exemple. Compare-le à ton rythme."));
      immediateRenderModel({...screen,model:screen.stimulus},region,null);
      region.append(immediateButton("Revenir au bloc",()=>immediateCommand("example-close"),true));
    }
  } else if(screen.phase==="masque") {
    region.append(immediateNode("p","…"));
    immediateSchedule(screen.remaining_ms||0,"mask-ended",immediateGeneration);
  } else if(screen.phase==="reponse") immediateResponse(screen,region);
  else if(screen.phase==="feedback") {
    immediateRenderFeedback(screen,region);
    if(screen.can_help) region.append(immediateButton("Revoir et essayer avec aide",()=>immediateCommand("help")));
    if(screen.help_interrupted)region.append(immediateNode("p","La seconde présentation a été interrompue. La première réponse est conservée ; tu peux réessayer avec aide."));
    region.append(immediateButton("Continuer",()=>immediateCommand("continue"),true));
  }
}

async function immediateSpeakCurrentDigit(screen) {
  if(screen.audio_digit==null)return;
  const speechKey=JSON.stringify([immediateView?.session_id,immediateView?.item_id,screen.revision,screen.audio_index,screen.example_stage||""]);
  if(immediateSpeechKey===speechKey)return;
  immediateSpeechKey=speechKey;
  if(typeof speechRequest!=="function" || (typeof speechCapabilities!=="undefined" && !speechCapabilities?.speech)) {
    immediateRegion().replaceChildren(immediateNode("p","Lecture audio indisponible sur cet appareil. Le parcours audio ne peut pas continuer.")); return;
  }
  const generation=immediateGeneration, token=`mi-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  immediateSpeechToken=token;
  const completed=new Promise(resolve=>{immediateSpeechResolve=resolve;});
  immediateSpeechWatchdog=setTimeout(()=>{
    if(immediateSpeechToken!==token)return;
    immediateSpeechToken=null;immediateSpeechWatchdog=null;immediateGeneration++;
    immediateAudioUnavailable("La lecture audio ne répond pas. Réessaie ou termine ce bloc ; le parcours visuel n’a pas été substitué.");
    speechRequest("cancel").catch(()=>{});const resolve=immediateSpeechResolve;immediateSpeechResolve=null;resolve?.("timeout");
  },15000);
  const failed=()=>{if(immediateSpeechToken!==token)return;immediateSpeechKey=null;clearTimeout(immediateSpeechWatchdog);immediateSpeechWatchdog=null;immediateSpeechToken=null;immediateGeneration++;
    immediateAudioUnavailable("Lecture audio indisponible sur cet appareil. Le parcours audio ne peut pas continuer en mode visuel.");const resolve=immediateSpeechResolve;immediateSpeechResolve=null;resolve?.("unavailable");};
  try { Promise.resolve(speechRequest("speak",{token,text:String(screen.audio_digit)})).catch(failed); }
  catch { failed(); }
  const result=await completed;
  if(result!=="finished"||generation!==immediateGeneration||paused)return;
  await immediateWait(screen.params?.intervalle_ms||0,generation);
  if(generation===immediateGeneration&&!paused)immediateCommand("audio-next");
}

function immediateNativeSpeechEvent(event) {
  if(event?.kind!=="speech"||event.token!==immediateSpeechToken)return false;
  if(["finished","stopped","unavailable","error"].includes(event.status)) {
    if(immediateSpeechWatchdog!==null)clearTimeout(immediateSpeechWatchdog);immediateSpeechWatchdog=null;
    immediateSpeechToken=null; const resolve=immediateSpeechResolve;immediateSpeechResolve=null;resolve?.(event.status);
    if(event.status!=="finished") immediateGeneration++;
    if(event.status!=="finished"){immediateSpeechKey=null;immediateAudioUnavailable(event.status==="stopped"?"La lecture a été interrompue. Tu peux réessayer ou terminer le bloc.":"Lecture audio indisponible sur cet appareil. Le parcours audio ne peut pas continuer en mode visuel.");}
  }
  return true;
}
window.immediateNativeSpeechEvent=immediateNativeSpeechEvent;
