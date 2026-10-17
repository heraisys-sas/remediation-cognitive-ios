const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

async function page({native = true} = {}) {
  const nodes = {};
  const get = id => nodes[id] ||= {textContent:'', value:'', hidden:false, disabled:false, focus(){}, blur(){}};
  const context = vm.createContext({performance:{now:()=>0}, document:{getElementById:get,
    querySelectorAll:()=>Object.values(nodes), querySelector:()=>get('heading'), addEventListener(){}},
    window:native ? {webkit:{messageHandlers:{runtime:{postMessage:async()=>({started:false})}}}} : {}});
  const source = path.resolve(__dirname, '../mobile/ios/pilot');
  vm.runInContext(fs.readFileSync(path.join(source,'active-clock.js'),'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(source,'pilot.js'),'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  return {get, render:value=>context.render(value)};
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
