"use strict";
const deductionDrafts=new Map();
function renderDeduction(view){
  const region=element('deduction');region.replaceChildren();
  region.hidden=view.activity!=='deduction'||!view.item||view.finished||paused;
  if(region.hidden)return;
  const content=view.item.contenu,n=content.figures.length,key=JSON.stringify([view.session_id,view.item.id,view.position]);
  const draft=deductionDrafts.get(key)||{cells:Array(n*n).fill(''),selected:null};deductionDrafts.set(key,draft);
  const line=text=>{const p=document.createElement('p');p.textContent=text;region.append(p);};
  line(content.consigne);
  for(const [index,clue] of content.enonces.entries())line(`${index+1}. ${formaterEnonce(clue,n)}`);
  const pieces=content.figures.flatMap(shape=>content.couleurs.map(color=>`${shape}:${color}`));
  if(view.feedback){
    const expected=String(view.feedback.attendue||'').split(';');
    line('Disposition attendue');const list=document.createElement('ol');
    for(const [index,value] of expected.entries()){
      const [shape,color]=value.split(':');const entry=document.createElement('li');entry.textContent=`Ligne ${Math.floor(index/n)+1}, colonne ${index%n+1} : ${libelleFigure(shape)} ${color||''}`;list.append(entry);
    }region.append(list);return;
  }
  line('Choisis une figure, puis touche sa case. Pour libérer une case, choisis Effacer.');
  const palette=document.createElement('div');palette.className='deductionPalette';region.append(palette);
  for(const value of [...pieces,'']){
    const button=document.createElement('button');button.type='button';button.className='secondaryButton';
    const [shape,color]=value.split(':');button.textContent=value?`${GLYPHES[shape]} ${libelleFigure(shape)} ${color}`:'Effacer';
    button.setAttribute('aria-pressed',String(draft.selected===value));
    button.onclick=()=>{draft.selected=value;renderDeduction(state);};palette.append(button);
  }
  const grid=document.createElement('div');grid.className='deductionGrid';grid.style.gridTemplateColumns=`repeat(${n},minmax(0,1fr))`;region.append(grid);
  for(const [index,value] of draft.cells.entries()){
    const button=document.createElement('button');button.type='button';button.id=`deduction-cell-${index}`;
    const [shape,color]=value.split(':');button.textContent=value?`${GLYPHES[shape]} ${color}`:'—';
    button.setAttribute('aria-label',`Ligne ${Math.floor(index/n)+1}, colonne ${index%n+1} : ${value?`${libelleFigure(shape)} ${color}`:'vide'}`);
    button.disabled=draft.selected===null;
    button.onclick=()=>{if(busy||paused||draft.selected===null)return;const old=draft.cells.indexOf(draft.selected);if(draft.selected&&old>=0)draft.cells[old]='';draft.cells[index]=draft.selected;renderDeduction(state);};grid.append(button);
  }
  const submit=document.createElement('button');submit.type='button';submit.textContent='Valider la grille';submit.id='deduction-submit';
  submit.disabled=draft.cells.some(value=>!value)||new Set(draft.cells).size!==n*n;
  submit.onclick=()=>{if(busy||paused||submit.disabled)return;return perform(async()=>{
    await request('answer',{session_id:view.session_id,item_id:view.item.id,answer:draft.cells.join(';'),elapsed_ms:Math.round(clock.elapsed())});render(await request('view'));
  });};region.append(submit);
}
