const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

async function page() {
  const nodes = {};
  const get = id => nodes[id] ||= {textContent:'', value:'', hidden:false, disabled:false, focus(){}, blur(){}};
  const context = vm.createContext({performance:{now:()=>0}, document:{getElementById:get,
    querySelectorAll:()=>Object.values(nodes), addEventListener(){}},
    window:{webkit:{messageHandlers:{runtime:{postMessage:async()=>({started:false})}}}}});
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
