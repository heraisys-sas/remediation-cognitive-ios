"use strict";
// Tâches effectivement portées ; descriptions fondées sur les fiches amont, sans score de capacité.
const homeCompetencies=[
  {id:'calcul',name:'Calculer de tête',description:'Pratiquer les opérations et les stratégies de calcul.',cards:[
    ['calcul-mental','Calcul mental','Calculer avec une méthode facultative, sans limite de temps imposée.']]},
  {id:'mots',name:'Retrouver les mots',description:'Chercher un mot à partir de sa définition, avec des indices si besoin.',cards:[
    ['acces-lexical','Retrouver le mot','Nommer le mot décrit, à voix haute ou au clavier.']]},
  {id:'memoire',name:'Retenir et manipuler des informations',description:'Garder des éléments en mémoire ; certains exercices demandent aussi de changer leur ordre.',cards:[
    ['chiffres-endroit','Chiffres dans l’ordre','Retenir des chiffres lus à l’écran et les restituer dans le même ordre.'],
    ['chiffres-envers','Chiffres en ordre inverse','Retenir des chiffres lus à l’écran et les restituer à l’envers.'],
    ['mots','Suites de mots','Retenir des mots lus à l’écran, dans l’ordre demandé : direct ou inverse selon le niveau.'],
    ['associations','Associations mot–nombre','Mémoriser des paires puis retrouver le nombre associé à un mot.'],
    ['position','Position dans une séquence','Mémoriser une suite de lettres, puis retrouver celle située au nombre de places demandé avant la fin.']]},
  {id:'contexte',name:'Associer une information à son contexte',description:'Associer un message à une scène, puis reconnaître son contexte sans la photo.',cards:[
    ['memoire-source','Retrouver le contexte','Découvrir des scènes et leurs messages, puis choisir le contexte correspondant parmi plusieurs propositions, sans photo.']]},
  {id:'organisation',name:'Préparer et vérifier une action',description:'Reconnaître une stratégie adaptée parmi des choix proposés.',cards:[
    ['choisir-plan','Choisir un plan','Choisir un plan d’étapes cohérent pour une situation.'],
    ['auto-instruction','Se guider avant d’agir','Choisir la question utile à se poser avant de commencer.'],
    ['verifier-plan','Vérifier un plan','Repérer l’étape à déplacer pour remettre un plan en ordre.']]},
  {id:'information',name:'Repérer une information',description:'Chercher une information utile dans un document qui reste visible.',cards:[
    ['chercher-information','Chercher dans un document','Consulter le document pour répondre à une question précise.']]},
  {id:'lecture',name:'Lire et retenir un texte',description:'Appliquer une méthode guidée de lecture, de reformulation et de rappel.',cards:[
    ['pqrst-guide','Lire avec PQRST, pas à pas','Parcourir, questionner, lire, reformuler, puis répondre sans le texte après un résumé modèle.']]}
];
let homeEnabled=homeCompetencies.map(item=>item.id),homeReady=false,homeSaving=false;
function renderHomeControls(){
  const disabled=busy||homeSaving||!homeReady;
  for(const item of homeCompetencies){const input=document.getElementById(`competency-${item.id}`);if(input)input.disabled=disabled;}
  for(const item of homeCompetencies)for(const card of item.cards){const button=document.getElementById(`activity-card-${card[0]}`);if(button)button.disabled=disabled;}
}
function renderHomeCards(){
  const region=element('activityCards');region.replaceChildren();
  if(!homeReady){element('homeStatus').textContent='Chargement des activités…';return;}
  const selected=homeCompetencies.filter(item=>homeEnabled.includes(item.id));
  element('homeStatus').textContent=selected.length?'Choisis une activité pour commencer.':'Aucune compétence sélectionnée. Choisis celles que tu souhaites travailler dans les paramètres.';
  for(const item of selected)for(const [id,name,description] of item.cards){
    const button=document.createElement('button');button.id=`activity-card-${id}`;button.className='activityCard';button.type='button';
    const title=document.createElement('strong');title.textContent=name;
    const detail=document.createElement('span');detail.textContent=description;
    button.append(title,detail);
    button.onclick=()=>{if(busy||homeSaving||!homeReady||!homeEnabled.includes(item.id)||state?.started&&!state.finished)return;
      element('activity').value=id;element('activity').onchange();return element('start').onclick();};
    region.append(button);
  }
  renderHomeControls();
}
function renderCompetencySettings(){
  const region=element('competencyChoices');region.replaceChildren();
  for(const item of homeCompetencies){
    const label=document.createElement('label');label.className='competencyChoice';
    const input=document.createElement('input');input.id=`competency-${item.id}`;input.type='checkbox';input.checked=homeEnabled.includes(item.id);
    const text=document.createElement('span');const title=document.createElement('strong');title.textContent=item.name;
    const description=document.createElement('span');description.textContent=item.description;
    const cards=document.createElement('small');cards.textContent=`Cartes : ${item.cards.map(card=>card[1]).join(' · ')}.`;
    text.append(title,description,cards);label.append(input,text);region.append(label);
    input.onchange=async()=>{
      if(busy||homeSaving||!homeReady){input.checked=homeEnabled.includes(item.id);return;}
      const previous=[...homeEnabled];const next=homeCompetencies.filter(entry=>entry.id===item.id?input.checked:homeEnabled.includes(entry.id)).map(entry=>entry.id);
      homeSaving=true;renderHomeControls();
      try{
        const saved=await speechRequest('set-home-settings',{enabled:next});
        homeEnabled=saved.enabled;renderHomeCards();element('competencyStatus').textContent='Choix enregistré. Les cartes de l’accueil sont mises à jour.';
      }catch(error){homeEnabled=previous;input.checked=previous.includes(item.id);element('competencyStatus').textContent=String(error.message||error);}
      finally{homeSaving=false;renderHomeControls();}
    };
  }
  renderHomeControls();
}
async function initializeHomeSettings(){
  try{
    const result=await speechRequest('home-settings');
    if(Array.isArray(result.enabled))homeEnabled=homeCompetencies.filter(item=>result.enabled.includes(item.id)).map(item=>item.id);
    element('competencyStatus').textContent='Ces choix affichent les activités souhaitées sur l’accueil.';
  }catch{element('competencyStatus').textContent='Personnalisation disponible dans l’application iPhone.';}
  homeReady=true;renderCompetencySettings();renderHomeCards();
}
