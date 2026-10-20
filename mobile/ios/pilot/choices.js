"use strict";
function isChoiceActivity(view) {
  return ["choisir-plan","auto-instruction","verifier-plan","chercher-information","cap-adapter","cap-verifier"].includes(view.activity);
}
function renderChoices(view) {
  const region=element("choices"); region.replaceChildren();
  region.hidden=!isChoiceActivity(view)||!view.item||Boolean(view.finished);
  if(region.hidden) return;
  const content=view.item.contenu;
  if(content.consigne) {
    const p=document.createElement("p"); p.textContent=content.consigne; region.append(p);
  }
  if(Array.isArray(content.plan)) {
    const list=document.createElement("ol"); list.setAttribute("aria-label","Plan à vérifier");
    for(const line of content.plan) {
      const item=document.createElement("li"); item.textContent=line; list.append(item);
    }
    region.append(list);
  }
  if(content.document) {
    const article=document.createElement("article"); article.setAttribute("aria-label","Document à consulter");
    article.textContent=content.document; region.append(article);
  }
  if(view.feedback) return;
  for(const [index,option] of (content.options||[]).entries()) {
    const button=document.createElement("button"); button.id=`choice-${index}`;
    button.className="protocolChoice"; button.textContent=option;
    button.onclick=()=>choiceAnswer(option); region.append(button);
  }
}
async function choiceAnswer(answer) {
  if(paused||!state?.item||!isChoiceActivity(state)) return;
  const payload={session_id:state.session_id,item_id:state.item.id,revision:state.choice_revision,
    answer,elapsed_ms:Math.round(clock.elapsed())};
  return perform(async()=>{
    let view;
    try { view=await request("choice-answer",payload); }
    catch(error) {
      const durable=await request("view").catch(()=>null);
      if(!durable || (!durable.finished&&durable.choice_revision===payload.revision)) throw error;
      view=durable;
    }
    // Le moteur additionne les segments validés, y compris après relance.
    clock.reset(paused); render(view);
  });
}
