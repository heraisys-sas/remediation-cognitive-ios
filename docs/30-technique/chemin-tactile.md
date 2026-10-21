# Refaire le chemin : traits et geste tactile

Le tracé de réponse était dessiné derrière le fond opaque des cases. La couche
SVG reste sans interception des gestes ; les cases de réponse et de correction
ont maintenant un fond transparent, avec des numéros d’ordre sur fond contrasté.
Les traits de trois pixels gardent une épaisseur constante quelle que soit la
taille de l’écran. Le modèle de correction affiche également les liaisons.

La réponse peut se préparer en glissant le doigt d’une case à l’autre, ou en
sélectionnant les cases séparément. Les événements de pointeur utilisent les
coordonnées des cases effectivement affichées ; les segments rapides sont
échantillonnés pour retenir les cases traversées dans l’ordre. Une même case
n’est pas ajoutée deux fois. Le nombre de choix ne dépasse pas la longueur du
protocole. Le second doigt est ignoré ; une annulation du geste n’enregistre pas
de réponse. Le clic synthétisé après le geste ne doit pas retirer une case.

Le bouton « Valider le chemin » conserve son rôle : le geste prépare seulement
un brouillon. Le bouton pour vider les cases, les touches fléchées et l’activation
au clavier restent disponibles. Le défilement est bloqué seulement sur la zone
de tracé pendant ce geste ; le reste de la page reste défilable.

La présentation conserve les cases éclairées successivement, sans tracé cumulatif
qui fournirait une aide supplémentaire. Aucun changement des stimuli, durées,
correcteurs, premières réponses ou historiques.

Validation sur ordinateur : 69 contrôles JavaScript réussis, dont cinq nouveaux
scénarios sur le geste, les doublons, l’annulation, les autres pointeurs, les
limites de longueur, l’absence d’enregistrement avant validation et les traits du
modèle. La vérification WebKit sur iPhone utilise des événements de pointeur
synthétiques et contrôle aussi les styles calculés ; elle ne remplace pas un
tracé physique au doigt par l’utilisateur.
