"use strict";
let autoLexical=null, autoLexicalKey=null, autoVoiceSession=null, autoPermission=false, autoMicro=null;
let autoReading=false;
const autoReadObservers=new Set(), autoReadItems=new Set(), autoKeyboardItems=new Set();
const lexicalItemKey=view=>JSON.stringify([view?.session_id,view?.item?.id,view?.position]);
function notifyAutoReading(active) {autoReading=active;for(const callback of [...autoReadObservers])callback(active);}
function abortAutoLexical() {
  autoLexical?.abort();autoLexical=null;autoLexicalKey=null;
}
async function authorizeAutoLexical(activity) {
  autoPermission=false;autoVoiceSession=null;
  if(activity!=="acces-lexical")return;
  try {
    if(!speechCapabilities) await initializeSpeech();
    if(!speechCapabilities?.on_device_dictation)return;
    const result=await speechRequest("authorize-dictation");autoPermission=result.authorized===true;
  } catch {autoPermission=false;}
}
function bindAutoLexicalSession(view) {
  if(autoPermission&&view.activity==="acces-lexical")autoVoiceSession=view.session_id;
}
function makeAutoMicro(callbacks,prepared=false) {
  const token=`auto-${++audioSerial}`;let cancelled=false,started=false;
  const fail=()=>{if(!cancelled&&autoMicro?.token===token)callbacks.onErreur?.();};
  const control={
    activer(){
      if(cancelled||started||paused||busy)return;
      started=true;
      if(prepared) speechRequest("activate-dictation",{token}).catch(fail);
      else {autoMicro={token,callbacks,control};speechRequest("start-dictation",{token}).catch(fail);}
    },
    abort(){cancelled=true;if(autoMicro?.token===token){autoMicro=null;speechRequest("cancel").catch(()=>{});}}
  };
  if(prepared){autoMicro={token,callbacks,control};speechRequest("prepare-dictation",{token}).then(result=>{if(result.ok===false)fail();}).catch(fail);}
  else control.activer();
  return control;
}
function receiveAutoSpeech(event) {
  if(event?.kind!=="dictation"||event.token!==autoMicro?.token)return false;
  const {callbacks}=autoMicro;
  if(event.status==="listening")callbacks.onDebut?.();
  else if(["partial","finishing"].includes(event.status)&&event.text)callbacks.onPartiel?.(event.text);
  else if(event.status==="finished") {autoMicro=null;if(event.text)callbacks.onResultat?.(event.text);callbacks.onFin?.();}
  else if(["denied","unavailable","interrupted","cancelled"].includes(event.status)){autoMicro=null;callbacks.onErreur?.();}
  return true;
}
function armAutoLexical() {
  const view=state;
  if(busy||paused||audioBusy||dictationDraft||!view?.item||view.feedback||view.finished||view.activity!=="acces-lexical"||view.item.type!=="rappel-indice"||autoVoiceSession!==view.session_id)return;
  const key=audioContextKey(view), itemKey=lexicalItemKey(view);
  if(autoKeyboardItems.has(itemKey)||autoLexicalKey===key)return;
  abortAutoLexical();autoLexicalKey=key;
  autoLexical=DicteeAuto.demarrer({
    capacites:{
      observerLecture(callback){autoReadObservers.add(callback);callback(autoReading);return()=>autoReadObservers.delete(callback);},
      lectureEnCours:()=>autoReading,
      preparerDictee:callbacks=>makeAutoMicro(callbacks,true),
      dicter:callbacks=>makeAutoMicro(callbacks)
    },
    verifier:transcription=>request("verify-dictation",{session_id:view.session_id,item_id:view.item.id,transcription}),
    afficher:text=>{if(audioContextKey(state)===key)element("answer").value=text;},
    statut:text=>{if(audioContextKey(state)===key)element("audioStatus").textContent=text;},
    clavier:available=>{
      autoLexical=null;autoLexicalKey=null;autoKeyboardItems.add(itemKey);
      if(available===false)autoVoiceSession=null;
      element("answer").focus();renderSpeechControls(state);
    },
    valider:text=>{
      autoLexical=null;autoLexicalKey=null;
      if(paused||busy||audioContextKey(state)!==key)return;
      element("answer").value=text;
      perform(async()=>{
        await request("answer",{session_id:view.session_id,item_id:view.item.id,answer:text,elapsed_ms:Math.round(clock.elapsed())});
        render(await request("view"));
      });
    }
  });
  if(!autoReadItems.has(itemKey)&&speechCapabilities?.speech) {
    autoReadItems.add(itemKey);
    const token=`read-${++audioSerial}`;speechToken=token;notifyAutoReading(true);
    speechRequest("speak",{token,text:speechTextForView(view).slice(0,12000)}).catch(()=>{
      if(speechToken===token){speechToken=null;notifyAutoReading(false);}
    });
  }
  renderSpeechControls(view);
}
