"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function fakeElement(tag) {
  return {tag, children:[], style:{values:{},setProperty(key,value){this.values[key]=value;}}, attrs:{}, className:"",
    classList:{values:[],add(value){this.values.push(value);}}, append(...nodes){this.children.push(...nodes);},
    replaceChildren(...nodes){this.children=[...nodes];}, setAttribute(key,value){this.attrs[key]=String(value);},
    addEventListener(){}, focus(){}, dataset:{}};
}
const source = fs.readFileSync(new URL("../mobile/ios/pilot/immediate.js", `file://${__filename}`), "utf8");
const document={createElement:fakeElement,createElementNS:(ns,tag)=>fakeElement(tag)};
const context = {window:{},console,document,busy:false,paused:false,
  element:()=>fakeElement("div"),rendered:null,
  clock:{elapsed:()=>0,reset(){}},
  request:async()=>({session_id:"s",item_id:"i",activity:"memoires-immediates",started:true,finished:false,immediate:{phase:"pret",revision:2,kind:"code",instruction:"Consigne"}}),
  perform:async fn=>fn(),
  render(view){context.rendered=view;context.immediateRender(view);}};
vm.createContext(context);
const result=vm.runInContext(`${source}\n;(async()=>{
  this.immediateRender=renderImmediate;
  const plan=immediateSequencePlan(["1","2","3"],2000,1000);
  if(JSON.stringify(plan.map(item=>[item.phase,item.duration_ms]))!==JSON.stringify([["element",2000],["blanc",1000],["element",2000],["blanc",1000],["element",2000]]))throw Error("sequence intervals or final hold changed");
  if(immediatePositionLabel({x:.15,y:.2})!=="En haut, à gauche")throw Error("path coordinate label mismatch");
  const path=immediateVisualGlyph("triangle","#abc").children[0];
  if(path.attrs.d!=="M40 8L73 69H7Z"||path.attrs.fill!=="#abc")throw Error("visual glyph geometry/color mismatch");
  const board=immediateBoard([{id:"a",x:.15,y:.2},{id:"b",x:.82,y:.3}]);
  if(board.cells[1].style.left!=="82%"||board.cells[1].style.top!=="30%")throw Error("stimulus positions were normalized away");
  immediateSpeechToken="active-token";let completed=false;immediateSpeechResolve=status=>{completed=status;};
  if(immediateNativeSpeechEvent({kind:"speech",token:"stale-token",status:"finished"})!==false)throw Error("stale token accepted");
  if(completed)throw Error("stale token completed audio");
  if(immediateNativeSpeechEvent({kind:"speech",token:"active-token",status:"partial"})!==true)throw Error("partial event was not routed");
  if(completed)throw Error("partial event completed audio");
  if(immediateNativeSpeechEvent({kind:"speech",token:"active-token",status:"finished"})!==true||completed!=="finished")throw Error("native completion did not release digit");
  immediateView={session_id:"s",item_id:"i",immediate:{revision:1,phase:"pret"}};
  await immediateCommand("show");
  if(!rendered||rendered.immediate.revision!==2)throw Error("root render did not update the current view");
  let sent; this.request=async(operation,payload)=>{sent=payload;return {session_id:"s",item_id:"i",immediate:{phase:"feedback",revision:4}};};
  immediateView={session_id:"s",item_id:"i",immediate:{revision:3,phase:"response",assisted:true}};
  await immediateCommand("answer",{response:"123"});
  if(sent.assisted!==true)throw Error("assisted response lost its provenance");
  immediateView={session_id:"s",item_id:"i",immediate:{revision:5,phase:"response",assisted:false}};
  await immediateCommand("answer",{response:"123"});
  if(sent.assisted!==false)throw Error("first response incorrectly marked assisted");
  await immediateCommand("show");
  if(Object.hasOwn(sent,"assisted"))throw Error("assistance flag leaked into non-answer operation");
})()`,context);
result.then(()=>{
  assert.match(source,/request\("immediate-step"/);
  assert.match(source,/audio_digit/);
  assert.match(source,/\["finished","stopped","unavailable","error"\]/);
  assert.doesNotMatch(source,/Pause/);
  console.log("immediate JavaScript contract: OK");
}).catch(error=>{console.error(error);process.exitCode=1;});
