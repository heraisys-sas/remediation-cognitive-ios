"use strict";
// Tâches effectivement portées ; descriptions fondées sur les fiches amont, sans score de capacité.
const homeCompetencies=[
  {id:'calcul',name:'Calculer de tête',description:'Pratiquer les opérations et les stratégies de calcul.',cards:[
    ['calcul-mental','Calcul mental','Calculer avec une méthode facultative, sans limite de temps imposée.']]},
  {id:'mots',name:'Retrouver les mots',description:'Retrouver un mot depuis sa définition ou en générant des caractéristiques qui le décrivent.',cards:[
    ['acces-lexical','Retrouver le mot','Nommer le mot décrit, à voix haute ou au clavier ; des indices sont disponibles si besoin.'],
    ['strategie-semantique','Décrire le mot par son sens (SFA)','Noter sa catégorie, son usage et son contexte avant de proposer le mot. Les notes ne sont pas notées.'],
    ['strategie-phonologique','Explorer les sons du mot (PCA)','Noter les caractéristiques phonologiques avant de proposer le mot. Les notes ne sont pas notées.']]},
  {id:'memoire',name:'Retenir et manipuler des informations',description:'Garder des éléments en mémoire ; certains exercices demandent aussi de changer leur ordre.',cards:[
    ['chiffres-endroit','Chiffres dans l’ordre','Retenir des chiffres lus à l’écran et les restituer dans le même ordre.'],
    ['chiffres-envers','Chiffres en ordre inverse','Retenir des chiffres lus à l’écran et les restituer à l’envers.'],
    ['mots','Suites de mots','Retenir des mots lus à l’écran, dans l’ordre demandé : direct ou inverse selon le niveau.'],
    ['associations','Associations mot–nombre','Mémoriser des paires puis retrouver le nombre associé à un mot.'],
    ['position','Position dans une séquence','Mémoriser une suite de lettres, puis retrouver celle située au nombre de places demandé avant la fin.'],
    ['series-lues-immediat','Mots lus — rappel immédiat','Mémoriser des séries de mots présentées à l’écran, puis rappeler les mots sans choix proposés.'],
    ['series-entendues-immediat','Mots entendus — rappel immédiat','Écouter des séries de mots, puis rappeler les mots sans choix proposés.'],
    ['series-lues-differe','Mots lus — rappel différé','Après les mots lus à l’écran, attendre 20 secondes puis rappeler les séries sans support.'],
    ['series-entendues-differe','Mots entendus — rappel différé','Après les mots entendus, attendre 20 secondes puis rappeler les séries sans support.'],
    ['series-lues-premiere-serie','Mots lus — première série seulement','Après plusieurs séries lues, rappeler uniquement les mots de la première série.'],
    ['series-entendues-premiere-serie','Mots entendus — première série seulement','Après plusieurs séries entendues, rappeler uniquement les mots de la première série.']]},
  {id:'contexte',name:'Associer une information à son contexte',description:'Associer un message à une scène, puis reconnaître son contexte sans la photo.',cards:[
    ['memoire-source','Retrouver le contexte','Découvrir des scènes et leurs messages, puis choisir le contexte correspondant parmi plusieurs propositions, sans photo.']]},
  {id:'organisation',name:'Préparer et vérifier une action',description:'Reconnaître une stratégie adaptée parmi des choix proposés.',cards:[
    ['choisir-plan','Choisir un plan','Choisir un plan d’étapes cohérent pour une situation.'],
    ['auto-instruction','Se guider avant d’agir','Choisir la question utile à se poser avant de commencer.'],
    ['verifier-plan','Vérifier un plan','Repérer l’étape à déplacer pour remettre un plan en ordre.'],
    ['cap-adapter','Adapter un plan','Mettre à jour un plan quand une information change, en gardant le but et les contraintes valables.'],
    ['cap-verifier','Vérifier avant de terminer','Comparer le résultat à la demande et repérer une discordance.'],
    ['cap-reprendre','Reprendre après une interruption','Contrôler le point où l’on s’était arrêté, puis reprendre le fil après un bref détour.']]},
  {id:'information',name:'Lire et comparer des informations',description:'Répondre à une question à partir d’un document visible ou repérer les éléments importants d’un dossier.',cards:[
    ['chercher-information','Chercher dans un document','Consulter un document qui reste visible pour répondre à une question précise.'],
    ['comparer-documents','Comparer deux documents','Comparer les champs des documents visibles et repérer les différences éventuelles.'],
    ['reperer-essentiel','Repérer l’essentiel','Trier des messages selon les critères de la tâche et du dossier.']]},
  {id:'lecture',name:'Lire et retenir un texte',description:'Appliquer une méthode guidée de lecture, de reformulation et de rappel.',cards:[
    ['pqrst-guide','PQRST guidé pas à pas','Parcourir, questionner, lire, reformuler, puis répondre à deux questions après un résumé modèle.'],
    ['pqrst-rappel','PQRST — répondre de mémoire','Lire le texte selon les étapes prévues, puis répondre aux questions de mémoire sans le texte.']]},
  {id:'deduction',name:'Résoudre des grilles de déduction',description:'Placer des pions en croisant les indices de chaque grille. Une aide facultative permet de noter les possibilités.',cards:[
    ['deduction','Déduction','Résoudre une grille en respectant ses indices ; les formes, couleurs et règles varient d’une grille à l’autre.']]},
  {id:'actualisation',name:'Actualiser une consigne',description:'Suivre une suite d’informations, puis écrire la consigne finale en conservant les éléments toujours valables.',cards:[
    ['actualiser-consigne','Actualiser une consigne','Lire les étapes successives d’une situation, puis compléter la consigne mise à jour.']]},
  {id:'quotidien',name:'Situations du quotidien',description:'Choisir une réponse ou une stratégie pour des situations courantes. Les choix à l’écran ne montrent pas ce qui sera fait dans la vie réelle.',cards:[
    ['quotidien','Situations du quotidien','Répondre à des questions sur des messages, des étapes, des durées, des rappels, des priorités et des aides externes.']]},
  {id:'apprentissages',name:'Apprentissages personnels',description:'Travailler des connaissances utiles en anglais et en programmation Python, sans objectif clinique.',cards:[
    ['anglais','Verbes irréguliers anglais','Retrouver activement des formes et du vocabulaire anglais.'],
    ['python','Lire du Python','Comprendre et restituer des notions, commandes ou résultats de courts extraits Python.']]},
  {id:'memoires-immediates',name:'Mémoires immédiates',description:'Essayer de courts blocs pour retenir un code, refaire un chemin, repérer un changement ou retrouver où se trouvaient des objets.',cards:[
    ['mi-code','Retenir un code','Observer ou écouter un code, puis le restituer.'],
    ['mi-chemin','Refaire le chemin','Observer une suite de positions, puis la reproduire.'],
    ['mi-changement','Qu’est-ce qui a changé ?','Comparer des présentations visuelles et indiquer si un élément a changé.'],
    ['mi-objets','Quel objet était où ?','Observer des objets et leurs emplacements, puis retrouver leur position.']]}
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
