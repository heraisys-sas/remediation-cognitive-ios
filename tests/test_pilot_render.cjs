const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

async function page({native = true, reply = async()=>({started:false}), speechReply = null} = {}) {
  const nodes = {};
  const create = tag => {
    const node = {tagName:tag, textContent:'', value:'', hidden:false, disabled:false, children:[], attrs:{}, focus(){}, blur(){},
      append(...items){this.children.push(...items);}, replaceChildren(...items){this.children=items;},
      setAttribute(key,value){this.attrs[key]=value;}};
    Object.defineProperty(node,'id',{set(value){nodes[value]=this;}, get(){return Object.keys(nodes).find(key=>nodes[key]===this);}});
    return node;
  };
  const get = id => nodes[id] ||= create();
  const context = vm.createContext({setTimeout,clearTimeout,performance:{now:()=>0}, document:{getElementById:get,
    querySelectorAll:()=>Object.values(nodes), querySelector:()=>get('heading'), createElement:create, addEventListener(){}},
    window:native ? {webkit:{messageHandlers:{runtime:{postMessage:reply}}}} : {}});
  if(speechReply&&native) context.window.webkit.messageHandlers.speech={postMessage:speechReply};
  const source = path.resolve(__dirname, '../mobile/ios/pilot');
  vm.runInContext(fs.readFileSync(path.join(source,'active-clock.js'),'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(source,'pqrst.js'),'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(source,'contextes.js'),'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(source,'choices.js'),'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(source,'memory.js'),'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(source,'speech.js'),'utf8'), context);
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

test('Contextes masque la saisie et la photo au rappel, et conserve le message incident',async()=>{
  const {get,render}=await page();
  const base={started:true,session_id:'s',position:1,total:10,activity:'memoire-source',item:{id:'i',type:'rappel-source',contenu:{enonce:'Contexte'}},contextes:{pass:'rappel',phase:'question',revision:1,options:['SMS','Carnet'],question:'Où ?'}};
  render(base);
  assert.equal(get('answerForm').hidden,true);
  assert.equal(get('next').hidden,true);
  assert.equal(get('contextes').children.some(n=>n.tagName==='img'),false);
  assert.equal(get('contextes-answer-0').textContent,'SMS');
  render({...base,contextes:{...base.contextes,pass:'decouverte',phase:'pret',options:[],image_failed:true}});
  assert.equal(get('contextes-show').textContent,'Réessayer');
  assert.ok(get('contextes').children.some(n=>n.textContent.includes('pas pu être chargée')));
});

test('une image décodée pendant un appel attend la disponibilité du pont',async()=>{
  const calls=[]; let view;
  const {get,context,render}=await page({reply:async payload=>{
    calls.push(payload);
    if(payload.action==='contextes-step') view={...view,contextes:{...view.contextes,phase:'exposition',revision:2}};
    return view||{started:false};
  }});
  view={started:true,session_id:'s',position:1,total:10,item:{id:'i',contenu:{enonce:'Contexte'}},contextes:{pass:'decouverte',phase:'photo',revision:1,image:{src:'images/a.webp',alt:'Message'},remaining_ms:12000}};
  let release;
  const work=context.perform(async()=>{
    render(view);
    const image=get('contextes').children.find(n=>n.tagName==='figure').children[0];
    image.onload(); // Décodage immédiat pendant perform.
    await new Promise(resolve=>{release=resolve;});
  });
  assert.equal(calls.some(c=>c.operation==='loaded'),false);
  release(); await work;
  await new Promise(resolve=>setTimeout(resolve,30));
  assert.equal(calls.filter(c=>c.operation==='loaded').length,1);
  context.stopContextesTimer();
});

test('les stratégies présentent les choix et gardent le second essai sans réponse révélée',async()=>{
  let current;
  const calls=[];
  const {get,render}=await page({reply:async payload=>{
    calls.push(payload);
    if(payload.action==='choice-answer') {
      current={...current,choice_revision:current.choice_revision+1,retry_feedback:'Essaie encore.'};
      return current;
    }
    return {started:false};
  }});
  current={started:true,activity:'choisir-plan',session_id:'s',choice_revision:0,item:{id:'i',contenu:{enonce:'Quel plan ?',options:['Courses puis menu','Menu puis courses'],consigne:'Repère le but.'}},position:1,total:8};
  render(current);
  assert.equal(get('answerForm').hidden,true);
  await get('choice-0').onclick();
  assert.equal(calls.at(-1).revision,0);
  assert.equal(calls.at(-1).answer,'Courses puis menu');
  assert.equal(get('feedback').textContent,'Essaie encore.');
  assert.equal(get('next').hidden,true);
  assert.equal(get('choice-1').disabled,false);
  assert.equal(get('choices').hidden,false);
});

test('chercher une information conserve le document pendant la réponse',async()=>{
  const {get,render}=await page();
  render({started:true,activity:'chercher-information',session_id:'s',choice_revision:0,item:{id:'i',contenu:{enonce:'Quand ?',document:'Rendez-vous le 19 mars.',options:['12 mars','19 mars']}}});
  assert.ok(get('choices').children.some(n=>n.tagName==='article'&&n.textContent==='Rendez-vous le 19 mars.'));
});

test('vérifier un plan montre ses étapes dans leur ordre source',async()=>{
  const {get,render}=await page();
  render({started:true,activity:'verifier-plan',session_id:'s',choice_revision:0,item:{id:'i',contenu:{enonce:'Quelle étape déplacer ?',plan:['Préparer','Peindre','Acheter'],options:['Acheter','Peindre']}}});
  const list=get('choices').children.find(n=>n.tagName==='ol');
  assert.ok(list);
  assert.deepEqual(list.children.map(n=>n.textContent),['Préparer','Peindre','Acheter']);
});

test('la mémoire montre un élément puis masque tout support au rappel',async()=>{
  const {get,render,context}=await page();
  const view={started:true,activity:'chiffres-endroit',session_id:'s',item:{id:'i',contenu:{enonce:'Mémorisation visuelle'}},memory:{phase:'element',revision:1,position:1,total:5,content:'7',remaining_ms:2000},position:1,total:12};
  render(view);
  assert.equal(get('answerForm').hidden,true);
  assert.ok(get('memory').children.some(n=>n.textContent==='7'));
  render({...view,memory:{phase:'question',revision:2,question:'Tape de mémoire.',inputmode:'numeric'}});
  assert.equal(get('answerForm').hidden,false);
  assert.ok(!get('memory').children.some(n=>n.textContent==='7'));
  assert.equal(get('answer').inputMode,'numeric');
  render({...view,memory:{phase:'question',revision:3,paused:true}});
  assert.equal(get('exercise').hidden,true);
  assert.equal(get('answerForm').hidden,true);
  context.stopMemoryTimer();
});

test('une réponse mémoire utilise la transition versionnée plutôt que la réponse générique',async()=>{
  const calls=[]; let view;
  const {get,render}=await page({reply:async payload=>{
    calls.push(payload);
    if(payload.action==='memory-step')return {...view,feedback:{correcte:true,attendue:'007'},memory:{...view.memory,revision:4}};
    return {started:false};
  }});
  view={started:true,activity:'chiffres-endroit',session_id:'s',item:{id:'i',contenu:{enonce:'Mémorisation visuelle'}},memory:{phase:'question',revision:3,question:'Tape de mémoire.',inputmode:'numeric'}};
  render(view);get('answer').value='007';
  await get('answerForm').onsubmit({preventDefault(){}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(calls.at(-1).action,'memory-step');
  assert.equal(calls.at(-1).operation,'answer');
  assert.equal(calls.at(-1).answer,'007');
  assert.equal(calls.at(-1).revision,3);
  assert.equal(get('next').hidden,false);
});

test('une interruption mémoire pendant une transition est sauvegardée après son retour',async()=>{
  const calls=[];let current,release;
  const {get,render,context}=await page({reply:async payload=>{
    calls.push(payload);
    if(payload.action==='view')return current;
    if(payload.operation==='show'){
      await new Promise(resolve=>{release=resolve;});
      current={...current,memory:{phase:'element',revision:1,content:'8',position:1,total:3,remaining_ms:2000}};
    } else if(payload.operation==='pause')current={...current,memory:{...current.memory,revision:2,paused:true,content:undefined}};
    return current;
  }});
  current={started:true,activity:'chiffres-endroit',session_id:'s',item:{id:'i',contenu:{enonce:'Mémoire'}},memory:{phase:'pret',revision:0,instruction:'Mémorise.'}};
  render(current);
  const submitted=get('memory-show').onclick();
  context.window.pauseForInterruption();release();await submitted;
  assert.equal(calls.at(-1).operation,'pause');
  assert.equal(calls.at(-1).revision,1);
  assert.equal(get('exercise').hidden,true);
  assert.equal(get('resume').hidden,false);
  context.stopMemoryTimer();
});

test('une avance mémoire en échec masque le stimulus et permet un renvoi sans réexposition',async()=>{
  const calls=[];let current,fail=true;
  const {get,render,context}=await page({reply:async payload=>{
    calls.push(payload);
    if(payload.action==='view')return current||{started:false};
    if(payload.operation==='advance'){
      if(fail)throw Error('Stockage indisponible');
      current={...current,memory:{phase:'question',revision:2,question:'Rappelle.',inputmode:'text'}};
      return current;
    }
  }});
  current={started:true,activity:'mots',session_id:'s',item:{id:'i',contenu:{enonce:'Mémoire'}},memory:{phase:'element',revision:1,content:'bouteille',position:1,total:4,remaining_ms:0}};
  render(current);await new Promise(resolve=>setTimeout(resolve,30));
  assert.equal(calls.filter(c=>c.operation==='advance').length,1);
  assert.ok(!get('memory').children.some(n=>n.textContent==='bouteille'));
  assert.match(get('error').textContent,/Stockage indisponible/);
  assert.equal(get('memory-retry').textContent,'Réessayer');
  const original=calls.find(c=>c.operation==='advance');
  fail=false;await get('memory-retry').onclick();
  assert.deepEqual(calls.at(-1),original);
  assert.equal(get('answerForm').hidden,false);
  context.stopMemoryTimer();
});

test('une avance mémoire validée malgré un retour perdu retrouve le rappel sans réexposition',async()=>{
  let current;
  const {get,render,context}=await page({reply:async payload=>{
    if(payload.action==='view')return current||{started:false};
    current={...current,memory:{phase:'question',revision:2,question:'Rappelle.',inputmode:'text'}};
    throw Error('Retour perdu');
  }});
  current={started:true,activity:'mots',session_id:'s',item:{id:'i',contenu:{enonce:'Mémoire'}},memory:{phase:'element',revision:1,content:'bouteille',position:1,total:4,remaining_ms:0}};
  render(current);await new Promise(resolve=>setTimeout(resolve,30));
  assert.equal(get('answerForm').hidden,false);
  assert.ok(!get('memory').children.some(n=>n.textContent==='bouteille'));
  assert.equal(get('error').textContent,'');
  context.stopMemoryTimer();
});

test('la lecture ne reçoit aucun support masqué ni indice non demandé',async()=>{
  const {context}=await page();
  const item={id:'i',contenu:{enonce:'Où ?',indices:[{texte:'Indice visible'},{texte:'Indice secret'}]}};
  const lexical={started:true,activity:'acces-lexical',item,hints_used:1};
  assert.match(context.speechTextForView(lexical),/Indice visible/);
  assert.doesNotMatch(context.speechTextForView(lexical),/secret/);
  const memory={...lexical,memory:{phase:'element',content:'SECRET'}};
  assert.equal(context.speechTextForView(memory),'');
  assert.equal(context.speechTextForView({...memory,memory:{phase:'question',question:'Rappelle.'}}),'Rappelle.');
  const pqrst={...lexical,protocol:{phase:'5.0',paragraphs:['Question T1'],options:['Lundi','Mardi']}};
  assert.equal(context.speechTextForView(pqrst),'Question T1\nLundi\nMardi');
  assert.equal(context.speechTextForView({...lexical,contextes:{phase:'question',question:'Où ?',image:{alt:'secret'}}}),'Où ?');
});

test('la dictée produit un brouillon modifiable sans soumettre de réponse',async()=>{
  const calls=[];
  const {get,render,context}=await page({reply:async payload=>{calls.push(payload);return {started:false};},speechReply:async payload=>{
    calls.push(payload);return payload.operation==='capabilities'?{speech:true,on_device_dictation:true}:{ok:true};
  }});
  const view={started:true,activity:'acces-lexical',session_id:'s',position:1,item:{id:'i',contenu:{enonce:'Retrouve le mot.'}}};
  render(view);get('answer').value='Une';await get('dictate').onclick();
  const token=calls.find(c=>c.operation==='start-dictation').token;
  context.window.nativeSpeechEvent({kind:'dictation',token,status:'partial',text:'bouteille'});
  assert.equal(get('answer').value,'Une bouteille');
  assert.equal(get('answer').readOnly,true);
  assert.equal(get('validate').disabled,true);
  context.window.nativeSpeechEvent({kind:'dictation',token,status:'finished',text:'bouteille'});
  assert.equal(get('answer').value,'Une bouteille');
  assert.equal(get('answer').readOnly,false);
  assert.equal(get('validate').disabled,false);
  assert.match(get('audioStatus').textContent,/Vérifie/);
  assert.ok(!calls.some(c=>c.action==='answer'||c.operation==='answer'));
});

test('l’interruption arrête la dictée et ignore les résultats tardifs',async()=>{
  const calls=[];
  const {get,render,context}=await page({speechReply:async payload=>{calls.push(payload);return payload.operation==='capabilities'?{speech:true,on_device_dictation:true}:{ok:true};}});
  render({started:true,activity:'acces-lexical',session_id:'s',position:1,item:{id:'i',contenu:{enonce:'Mot ?'}}});
  await get('dictate').onclick();const token=calls.find(c=>c.operation==='start-dictation').token;
  context.window.nativeSpeechEvent({kind:'dictation',token,status:'partial',text:'premier brouillon'});
  context.window.pauseForInterruption();
  assert.ok(calls.some(c=>c.operation==='cancel'));
  context.window.nativeSpeechEvent({kind:'dictation',token,status:'finished',text:'résultat tardif'});
  assert.equal(get('answer').value,'premier brouillon');
  assert.equal(get('answer').readOnly,false);
});

test('la dictée refusée rend le clavier sans modifier le brouillon',async()=>{
  const calls=[];
  const {get,render,context}=await page({speechReply:async payload=>{calls.push(payload);return payload.operation==='capabilities'?{speech:true,on_device_dictation:true}:{ok:true};}});
  render({started:true,activity:'acces-lexical',session_id:'s',item:{id:'i',contenu:{enonce:'Mot ?'}}});
  get('answer').value='Mon texte';await get('dictate').onclick();
  const token=calls.find(c=>c.operation==='start-dictation').token;
  context.window.nativeSpeechEvent({kind:'dictation',token,status:'denied'});
  assert.equal(get('answer').value,'Mon texte');assert.equal(get('answer').readOnly,false);
  assert.match(get('audioStatus').textContent,/clavier/);
});

test('la dictée PQRST conserve le brouillon et respecte les étapes sans saisie libre',async()=>{
  const calls=[];
  const {get,render,context}=await page({speechReply:async payload=>{calls.push(payload);return payload.operation==='capabilities'?{speech:true,on_device_dictation:true}:{ok:true};}});
  const base={started:true,activity:'pqrst-guide',session_id:'s',position:1,item:{id:'i',type:'pqrst-mise-en-oeuvre',contenu:{enonce:'PQRST'}},protocol:{phase:'4',revision:3,paragraphs:['Reformule.'],actions:[],input_label:'Reformulation',response_label:'Valider'}};
  render(base);await get('dictate').onclick();const token=calls.find(c=>c.operation==='start-dictation').token;
  context.window.nativeSpeechEvent({kind:'dictation',token,status:'finished',text:'Le colis attend.'});
  assert.equal(get('protocol-answer').value,'Le colis attend.');
  assert.equal(get('protocol-respond').disabled,false);
  render(base);assert.equal(get('protocol-answer').value,'Le colis attend.');
  render({...base,protocol:{phase:'5.0',revision:4,paragraphs:['T1'],options:['A','B'],actions:[],response_label:'Valider'}});
  assert.equal(get('dictate').hidden,true);
});

test('un changement d’étape coupe la lecture avant l’appel au moteur',async()=>{
  const calls=[];
  const {get,render}=await page({reply:async payload=>{calls.push(payload);return {started:false};},speechReply:async payload=>{calls.push(payload);return payload.operation==='capabilities'?{speech:true,on_device_dictation:true}:{ok:true};}});
  render({started:true,activity:'acces-lexical',session_id:'s',position:1,item:{id:'i',contenu:{enonce:'Question',indices:[{texte:'secret'}]}},hints_used:0});
  await get('listen').onclick();
  assert.equal(calls.find(c=>c.operation==='speak').text,'Question');
  await get('hint').onclick();
  const cancel=calls.findIndex(c=>c.operation==='cancel');const hint=calls.findIndex(c=>c.action==='hint');
  assert.ok(cancel>=0&&hint>cancel);
});

test('un démarrage de dictée en attente est invalidé par une pause',async()=>{
  const calls=[];let release;
  const {get,render,context}=await page({speechReply:async payload=>{
    calls.push(payload);
    if(payload.operation==='capabilities')return {speech:true,on_device_dictation:true};
    if(payload.operation==='cancel')await new Promise(resolve=>{release=resolve;});
    return {ok:true};
  }});
  render({started:true,activity:'acces-lexical',session_id:'s',position:1,item:{id:'i',contenu:{enonce:'Question'}}});
  await get('listen').onclick();const starting=get('dictate').onclick();
  context.window.pauseForInterruption();release();await starting;
  assert.ok(!calls.some(c=>c.operation==='start-dictation'));
  assert.equal(get('exercise').hidden,true);
});

test('un démarrage audio en attente ne traverse pas un changement d’étape PQRST',async()=>{
  const calls=[];let release;
  const {get,render,context}=await page({speechReply:async payload=>{
    calls.push(payload);
    if(payload.operation==='capabilities')return {speech:true,on_device_dictation:true};
    if(payload.operation==='cancel')await new Promise(resolve=>{release=resolve;});
    return {ok:true};
  }});
  const view={started:true,activity:'pqrst-guide',session_id:'s',position:1,item:{id:'i',type:'pqrst-mise-en-oeuvre',contenu:{enonce:'PQRST'}},protocol:{phase:'Q',revision:2,input_label:'Question',paragraphs:['Q'],actions:[],response_label:'Valider'}};
  render(view);await get('listen').onclick();const starting=get('dictate').onclick();
  await context.perform(async()=>render({...view,protocol:{phase:'Q-retour',revision:3,paragraphs:['Retour'],actions:[]}}));
  release();await starting;
  assert.ok(!calls.some(c=>c.operation==='start-dictation'));
  assert.equal(get('dictate').hidden,true);
});

test('un indice pendant la dictée ne laisse pas Valider grisé après son arrêt',async()=>{
  let current; const calls=[];
  const {get,render,context}=await page({reply:async payload=>{
    calls.push(payload);
    if(payload.action==='hint')return {...current,hints_used:1};
    return {started:false};
  },speechReply:async payload=>{
    calls.push(payload);return payload.operation==='capabilities'?{speech:true,on_device_dictation:true}:{ok:true};
  }});
  current={started:true,activity:'acces-lexical',session_id:'s',position:1,hints_used:0,item:{id:'i',contenu:{enonce:'Mot ?',indices:[{texte:'Un objet'}]}}};
  render(current);await get('dictate').onclick();
  const token=calls.find(c=>c.operation==='start-dictation').token;
  context.window.nativeSpeechEvent({kind:'dictation',token,status:'partial',text:'bouteille'});
  assert.equal(get('validate').disabled,true);
  await get('hint').onclick();
  assert.equal(get('answer').value,'bouteille');
  assert.equal(get('answer').readOnly,false);
  assert.equal(get('validate').disabled,false);
});
