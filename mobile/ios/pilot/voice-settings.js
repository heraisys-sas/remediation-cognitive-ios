"use strict";
let voiceSettingsReady=false,voiceSettingsBusy=false;
function renderVoiceSettingsControls(){
  element('voiceChoice').disabled=element('previewVoice').disabled=busy||voiceSettingsBusy||!voiceSettingsReady;
}
async function initializeVoiceSettings(){
  const select=element('voiceChoice'),preview=element('previewVoice'),status=element('voiceSettingsStatus');
  try {
    const result=await speechRequest('voices');
    const voices=(result.voices||[]).filter(voice=>voice.language?.startsWith('fr-')&&!voice.identifier?.includes('com.apple.eloquence.'));
    select.replaceChildren();
    for(const voice of voices){
      const option=document.createElement('option');option.value=voice.identifier;
      const region=voice.language==='fr-FR'?'France':voice.language==='fr-CA'?'Canada':voice.language;
      const quality=voice.quality===3?' · premium':voice.quality===2?' · améliorée':'';
      option.textContent=`${voice.name} · ${region}${quality}`;select.append(option);
    }
    select.value=result.selected||voices[0]?.identifier||'';
    voiceSettingsReady=Boolean(voices.length);renderVoiceSettingsControls();
    status.textContent=voices.length?'Voix installées sur cet iPhone. Ton choix est mémorisé.':'Aucune voix française compatible disponible.';
    let selected=select.value;
    select.onchange=async()=>{
      voiceSettingsBusy=true;renderVoiceSettingsControls();
      try{
        if(speechToken){await speechRequest('stop-speaking');speechToken=null;}
        const saved=await speechRequest('set-voice',{identifier:select.value});select.value=saved.selected;selected=saved.selected;
        status.textContent='Voix de lecture enregistrée.';
      }catch(error){select.value=selected;status.textContent=String(error.message||error);}
      finally{voiceSettingsBusy=false;renderVoiceSettingsControls();}
    };
    preview.onclick=async()=>{
      if(busy||paused||state?.item&&!state.finished)return;
      voiceSettingsBusy=true;renderVoiceSettingsControls();
      try{
        const token=`voice-preview-${++audioSerial}`;speechToken=token;
        await speechRequest('speak',{token,text:'Bonjour. Nous allons avancer ensemble, une question à la fois.'});
      }catch(error){speechToken=null;status.textContent=String(error.message||error);}
      finally{voiceSettingsBusy=false;renderVoiceSettingsControls();}
    };
  }catch{
    voiceSettingsReady=false;renderVoiceSettingsControls();status.textContent='Le choix de voix est disponible dans l’application iPhone.';
  }
}
