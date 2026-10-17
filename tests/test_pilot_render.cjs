const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

async function page({native = true, reply = async()=>({started:false})} = {}) {
  const nodes = {};
  const create = () => {
    const node = {textContent:'', value:'', hidden:false, disabled:false, children:[], attrs:{}, focus(){}, blur(){},
      append(...items){this.children.push(...items);}, replaceChildren(...items){this.children=items;},
      setAttribute(key,value){this.attrs[key]=value;}};
    Object.defineProperty(node,'id',{set(value){nodes[value]=this;}, get(){return Object.keys(nodes).find(key=>nodes[key]===this);}});
    return node;
  };
  const get = id => nodes[id] ||= create();
  const context = vm.createContext({performance:{now:()=>0}, document:{getElementById:get,
    querySelectorAll:()=>Object.values(nodes), querySelector:()=>get('heading'), createElement:create, addEventListener(){}},
    window:native ? {webkit:{messageHandlers:{runtime:{postMessage:reply}}}} : {}});
  const source = path.resolve(__dirname, '../mobile/ios/pilot');
  vm.runInContext(fs.readFileSync(path.join(source,'active-clock.js'),'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(source,'pqrst.js'),'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(source,'pilot.js'),'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  return {get, render:value=>context.render(value), context};
}

test('la reprise expose le support sans révéler la réponse au premier passage', async()=>{
  const {get,render} = await page();
  const view = {started:true, item:{contenu:{enonce:'47 + 38 ?'}}, position:1, total:12};
  render(view);
  assert.equal(get('repriseSupport').hidden,true);
  render({...view,reprise:true,reprise_attendue:85});
  assert.equal(get('repriseSupport').hidden,false);
  assert.match(get('repriseSupport').textContent,/85/);
});

test('PQRST masque la saisie générique et ne réactive pas une réponse vide après sauvegarde', async()=>{
  const protocol = {revision:1,phase:'P',paused:false,paragraphs:['Sujet'],actions:[],options:['colis','recette'],
    response_label:'Valider',absence_label:'Je ne sais pas',can_reread:false};
  const view = {started:true,session_id:'s',item:{id:'i',type:'pqrst-mise-en-oeuvre',contenu:{enonce:'PQRST'}},protocol};
  const calls=[];
  const {get,render} = await page({reply:async payload=>{
    calls.push(payload);
    return payload.action==='pqrst-step' ? {...view,protocol:{...protocol,revision:2,phase:'Q',options:null,input_label:'Votre question'}} : {started:false};
  }});
  render(view);
  assert.equal(get('answerForm').hidden,true);
  assert.equal(get('protocol-respond').disabled,true);
  get('protocol-option-0').onclick();
  assert.equal(get('protocol-respond').disabled,false);
  assert.equal(get('protocol-option-0').attrs['aria-pressed'],'true');
  await get('protocol-respond').onclick();
  assert.equal(calls.at(-1).value,'colis');
  assert.equal(calls.at(-1).revision,1);
  assert.equal(get('protocol-respond').disabled,true);
  assert.equal(get('protocol-answer').maxLength,2000);
});

test('une pause pendant un appel PQRST est enregistrée après la transition', async()=>{
  const protocol = {revision:1,phase:'R',paused:false,paragraphs:['Lecture'],actions:[{operation:'continue',label:'Continuer'}],options:null};
  const view = {started:true,session_id:'s',item:{id:'i',type:'pqrst-mise-en-oeuvre',contenu:{enonce:'PQRST'}},protocol};
  let current=view, release;
  const calls=[];
  const {get,render,context} = await page({reply:async payload=>{
    calls.push(payload);
    if(payload.action==='view') return current;
    if(payload.operation==='continue') {
      await new Promise(resolve=>{release=resolve;});
      current={...view,protocol:{...protocol,revision:2,phase:'4',paragraphs:['Sans texte'],actions:[],input_label:'Reformulation'}};
    } else if(payload.operation==='pause') current={...current,protocol:{...current.protocol,revision:3,paused:true,paragraphs:[]}};
    return current;
  }});
  render(view);
  const submitting=get('protocol-continue').onclick();
  context.window.pauseForInterruption();
  release(); await submitting;
  assert.equal(calls.at(-1).operation,'pause');
  assert.equal(calls.at(-1).revision,2);
  assert.equal(get('exercise').hidden,true);
  assert.equal(get('resume').hidden,false);
});

test('une pause PQRST conserve le brouillon et les choix sans les valider', async()=>{
  let responseView;
  const {get,render} = await page({reply:async payload=>payload.operation==='resume' ? responseView : {started:false}});
  const protocol={revision:1,phase:'4',paragraphs:['Sans texte'],paused:false,actions:[],input_label:'Reformulation',
    response_label:'Valider',absence_label:'Je ne sais pas'};
  const view={started:true,session_id:'s',position:1,item:{id:'i',type:'pqrst-mise-en-oeuvre',contenu:{enonce:'PQRST'}},protocol};
  render(view);
  get('protocol-answer').value='Mon brouillon non validé'; get('protocol-answer').oninput();
  render({...view,protocol:{...protocol,paused:true,paragraphs:[]}});
  responseView=view; await get('resume').onclick();
  assert.equal(get('protocol-answer').value,'Mon brouillon non validé');
  assert.equal(get('protocol-respond').disabled,false);
  const choiceView={...view,protocol:{...protocol,phase:'5.0',input_label:null,options:['jeudi','samedi']}};
  render(choiceView); get('protocol-option-1').onclick();
  render({...choiceView,protocol:{...choiceView.protocol,paused:true}});
  responseView=choiceView; await get('resume').onclick();
  assert.equal(get('protocol-option-1').attrs['aria-pressed'],'true');
});

test('le retour PQRST explique P et le résumé exclut les compteurs lexicaux', async()=>{
  const {get,render,context} = await page();
  const lines=context.pqrstFeedbackLines({sequence:{'1':{correcte:false,attendue:'un colis'},observation:{statuts:{'1':'reponse'},tentatives:{}}}});
  assert.match(lines.join('\n'),/sujet du texte : réponse à revoir/);
  assert.match(lines.join('\n'),/après le résumé modèle/);
  render({started:true,finished:true,activity:'pqrst-guide',summary:{resume:{items:1,correctes:0,sans_aide:0,assistees:0}}});
  assert.doesNotMatch(get('summaryText').textContent,/sans aide|mot affiché/);
});

test('un retour natif perdu restaure la nouvelle étape au lieu de bloquer', async()=>{
  const protocol={revision:1,phase:'Q',paragraphs:['Question'],paused:false,actions:[],input_label:'Votre question',
    response_label:'Valider',absence_label:'Je ne sais pas'};
  const view={started:true,session_id:'s',position:1,item:{id:'i',type:'pqrst-mise-en-oeuvre',contenu:{enonce:'PQRST'}},protocol};
  let current={started:false};
  const {get,render} = await page({reply:async payload=>{
    if(payload.action==='view') return current;
    current={...view,protocol:{...protocol,revision:2,phase:'Q-retour',input_label:null,actions:[{operation:'continue',label:'Lire'}]}};
    throw Error('retour perdu après enregistrement');
  }});
  render(view); get('protocol-answer').value='Que retenir ?'; get('protocol-answer').oninput();
  await get('protocol-respond').onclick();
  assert.equal(get('protocol-continue').textContent,'Lire');
  assert.equal(get('error').textContent,'');
});

test('une pause non enregistrée reste masquée jusqu’à sa reprise durable', async()=>{
  const protocol={revision:1,phase:'4',paragraphs:['Sans texte'],paused:false,actions:[],input_label:'Reformulation',
    response_label:'Valider',absence_label:'Je ne sais pas'};
  const view={started:true,session_id:'s',position:1,item:{id:'i',type:'pqrst-mise-en-oeuvre',contenu:{enonce:'PQRST'}},protocol};
  let current={started:false}, failPause=true;
  const calls=[];
  const {get,render,context}=await page({reply:async payload=>{
    calls.push(payload);
    if(payload.action==='view') return current;
    if(payload.operation==='pause') {
      if(failPause) throw Error('stockage indisponible');
      current={...view,protocol:{...protocol,revision:2,paused:true,paragraphs:[]}};
    } else if(payload.operation==='resume') current={...view,protocol:{...protocol,revision:3}};
    return current;
  }});
  current=view; render(view);
  get('protocol-answer').value='Ma première formulation'; get('protocol-answer').oninput();
  await context.window.pauseForInterruption();
  await get('resume').onclick();
  assert.equal(get('exercise').hidden,true);
  assert.equal(calls.some(call=>call.operation==='resume'),false);
  failPause=false;
  await get('resume').onclick();
  assert.equal(get('exercise').hidden,false);
  assert.equal(calls.at(-1).operation,'resume');
  assert.equal(get('protocol-answer').value,'Ma première formulation');
});

test('les indices lexicaux restent facultatifs et sont restaurés dans l’ordre', async()=>{
  const {get,render} = await page();
  const view = {started:true,title:'Retrouver le mot',activity:'acces-lexical',
    item:{type:'rappel-indice',contenu:{enonce:'Définition',indices:[{texte:'Catégorie : bureau'},{texte:'Commence par a'}]}},hints_used:1};
  render(view);
  assert.equal(get('heading').textContent,'Retrouver le mot');
  assert.equal(get('activityChoice').hidden,true);
  assert.equal(get('lexicalHelp').hidden,false);
  assert.equal(get('hints').textContent,'Catégorie : bureau');
  assert.equal(get('hint').hidden,false);
  render({...view,hints_used:2});
  assert.equal(get('hint').hidden,true);
  assert.match(get('hints').textContent,/Commence par a/);
  render({...view,feedback:{assistee:true,attendue:'agrafeuse'}});
  assert.equal(get('lexicalHelp').hidden,true);
  assert.equal(get('answerForm').hidden,true);
});

test('la page hors app explique le lancement nécessaire sans erreur WebKit brute', async()=>{
  const {get} = await page({native:false});
  assert.match(get('error').textContent,/ouvre l’application/);
  assert.doesNotMatch(get('error').textContent,/undefined|messageHandlers/);
});

test('la durée propose un arrêt tout en laissant les commandes disponibles', async()=>{
  const {get,render} = await page();
  render({started:true, item:{contenu:{enonce:'47 + 38 ?'}}, position:1, total:12, arret_propose:true});
  assert.equal(get('stopProposal').hidden,false);
  assert.equal(get('finish').hidden,false);
  assert.equal(get('validate').disabled,false);
});

test('la fatigue du résumé invite à la pause sans bloquer une nouvelle séance', async()=>{
  const {get,render} = await page();
  render({started:true,finished:true,summary:{resume:{items:3,correctes:0},arret_propose:true,motif_arret:'fatigue'}});
  assert.equal(get('summaryAdvice').hidden,false);
  assert.equal(get('start').hidden,false);
  assert.equal(get('start').disabled,false);
});
