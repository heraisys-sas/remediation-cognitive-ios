"""Correction explicite des trois tâches fonctionnelles, sans similarité approximative."""
from .correction import _clef_reponse

TYPES = frozenset({'actualiser-consigne', 'comparer-documents', 'reperer-essentiel',
                   'reprise-interrompue'})

def corriger_detail(item, reponse):
    c = item['contenu']
    attendu = item['reponse']['valeur']
    donne = reponse if isinstance(reponse, dict) else {}
    if item['type'] == 'reprise-interrompue':
        points_donnes = donne.get('points') if isinstance(donne.get('points'), dict) else {}
        points_attendus = attendu['points']
        labels = {point['id']: point['label'] for point in c['points']}
        lignes = []
        for cle, valeur in points_attendus.items():
            correcte = points_donnes.get(cle) == valeur
            lignes.append({'label': labels[cle], 'correcte': correcte,
                           'attendue': {'valide': 'Déjà validé',
                                       'reprendre': 'À reprendre'}[valeur],
                           'explication': ''})
        reprise = donne.get('reprise')
        reprise_attendue = attendu['reprise']
        reprise_correcte = reprise == reprise_attendue
        lignes.append({'label': 'Reprise après interruption',
                       'correcte': reprise_correcte,
                       'attendue': f'Reprendre par « {labels[reprise_attendue]} »',
                       'explication': 'Le point précédent était déjà traité.'})
        complete = set(points_donnes) == set(points_attendus)
        return complete and reprise_correcte and all(l['correcte'] for l in lignes), {
            'lignes': lignes, 'omissions': 0, 'fausses_selections': 0,
            'type': item['type'], 'interruption_non_notee': True,
        }
    champs = c.get('champs') or [{'id':m['id'],'label':m['texte']} for m in c['messages']]
    lignes=[]
    omissions=fausses_selections=0
    for champ in champs:
        key=champ['id']; valeur=attendu[key]; fournie=donne.get(key)
        juste = isinstance(fournie, str) and _clef_reponse(fournie)==_clef_reponse(valeur)
        if item['type']=='reperer-essentiel':
            omissions += valeur=='oui' and fournie!='oui'
            fausses_selections += valeur=='non' and fournie=='oui'
        label={'oui':'À prendre en compte','non':'Sans conséquence selon les critères',
               'ecart':'Écart à corriger','conforme':'Conforme'}.get(valeur,valeur)
        lignes.append({'label':champ['label'],'correcte':juste,'attendue':label,
                       'explication':item['reponse'].get('explications',{}).get(key,'')})
    return all(l['correcte'] for l in lignes) and set(donne)==set(attendu), {
        'lignes':lignes,'omissions':omissions,'fausses_selections':fausses_selections,
        'type':item['type'],
    }
