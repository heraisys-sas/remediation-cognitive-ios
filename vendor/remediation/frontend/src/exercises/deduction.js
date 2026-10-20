"use strict";

const NOMS_COLONNES_4 = ["1", "2", "3", "4"];

const NOMS_LIGNES_4 = ["1", "2", "3", "4"];

const NOMS_CASES_4 = [
  "en haut à gauche", "en haut, deuxième", "en haut, troisième", "en haut à droite",
  "deuxième ligne à gauche", "deuxième ligne, deuxième", "deuxième ligne, troisième", "deuxième ligne à droite",
  "troisième ligne à gauche", "troisième ligne, deuxième", "troisième ligne, troisième", "troisième ligne à droite",
  "en bas à gauche", "en bas, deuxième", "en bas, troisième", "en bas à droite",
];

const NOMS_COLONNES_3 = ["de gauche", "du centre", "de droite"];

const NOMS_LIGNES_3 = ["du haut", "du milieu", "du bas"];

const NOMS_CASES_3 = [
  "en haut à gauche", "en haut au centre", "en haut à droite",
  "au milieu à gauche", "au centre", "au milieu à droite",
  "en bas à gauche", "en bas au centre", "en bas à droite",
];

const TEINTES = { rouge: "#e2574c", bleu: "#5b8dd9", vert: "#5aa469", jaune: "#d9b04a" };

const LIBELLES_FIGURES = { cercle: "cercle", carre: "carré", triangle: "triangle", losange: "losange" };

const GLYPHES = { cercle: "●", carre: "■", triangle: "▲", losange: "◆" };

function textePourLectureDeduction(
  contenu,
  inclureConsigne = true,
  formateur = formaterEnonce,
) {
  const n = Array.isArray(contenu.figures) ? contenu.figures.length : 3;
  const indices = Array.isArray(contenu.enonces)
    ? contenu.enonces.map((indice) => formateur(indice, n)).filter(Boolean)
    : [];
  return [inclureConsigne ? contenu.consigne : "", indices.length ? "Indices." : "", ...indices]
    .filter(Boolean)
    .join(" ");
}

function texteAutomatiquePourDeduction(
  contenu,
  consignesLues = etat.consignesAudioVues,
  formateur = formaterEnonce,
) {
  const consigne = String(contenu.consigne || "").trim();
  const dejaLue = Boolean(consigne && consignesLues.has(consigne));
  if (consigne) consignesLues.add(consigne);
  return textePourLectureDeduction(contenu, !dejaLue, formateur);
}

function nomsPour(n) {
  return {
    cases: n === 4 ? NOMS_CASES_4 : NOMS_CASES_3,
    lignes: n === 4 ? NOMS_LIGNES_4 : NOMS_LIGNES_3,
    colonnes: n === 4 ? NOMS_COLONNES_4 : NOMS_COLONNES_3,
  };
}

function predicatAtome(atome, n) {
  const noms = nomsPour(n);
  switch (atome.type) {
    case "case": return { texte: `${noms.cases[atome.case]}`, negation: null };
    case "ligne": return { texte: `sur la ligne ${noms.lignes[atome.ligne]}`, negation: null };
    case "colonne": return { texte: `dans la colonne ${noms.colonnes[atome.colonne]}`, negation: null };
    case "pas-ligne": return { texte: `sur la ligne ${noms.lignes[atome.ligne]}`, negation: "pas" };
    case "pas-colonne": return { texte: `dans la colonne ${noms.colonnes[atome.colonne]}`, negation: "pas" };
    case "coin": return { texte: "dans un coin", negation: null };
    case "diagonale": return { texte: "sur la diagonale descendante (du coin haut gauche au coin bas droit)", negation: null };
    case "diagonale-inverse": return { texte: "sur la diagonale montante (du coin haut droit au coin bas gauche)", negation: null };
    case "pas-diagonale": return { texte: "sur la diagonale descendante", negation: "pas" };
    case "pas-diagonale-inverse": return { texte: "sur la diagonale montante", negation: "pas" };
    case "pas-coin": return { texte: "dans un coin", negation: "pas" };
    case "pas-bord": return { texte: "sur le bord", negation: "pas" };
    case "ni-ni": return { texte: "dans un coin ni sur le bord", negation: "ni" };
    default: return { texte: "", negation: null };
  }
}

function relationAtome(atome, n) {
  const cible = `${libelleFigure(atome.figure2)} ${atome.couleur2}`;
  switch (atome.type) {
    case "voisin-gauche": return `est juste à gauche du ${cible}`;
    case "voisin-droite": return `est juste à droite du ${cible}`;
    case "voisin-dessus": return `est juste au-dessus du ${cible}`;
    case "voisin-dessous": return `est juste en dessous du ${cible}`;
    case "pas-voisin-gauche": return `n'est pas juste à gauche du ${cible}`;
    case "pas-voisin-droite": return `n'est pas juste à droite du ${cible}`;
    case "pas-voisin-dessus": return `n'est pas juste au-dessus du ${cible}`;
    case "pas-voisin-dessous": return `n'est pas juste en dessous du ${cible}`;
    case "pas-a-droite-de": return `n'est pas plus à droite que le ${cible}`;
    case "pas-a-gauche-de": return `n'est pas plus à gauche que le ${cible}`;
    case "pas-au-dessus-de": return `n'est pas plus haut que le ${cible}`;
    case "pas-en-dessous-de": return `n'est pas plus bas que le ${cible}`;
    case "voisin-diagonale": return `touche le ${cible} en diagonale`;
    case "oppose": return `est à l'opposé du ${cible}, de l'autre côté du centre`;
    case "comparaison": return `est sur la même ligne que le ${cible}, à sa gauche`;
    case "a-droite-de": return `est plus à droite que le ${cible}`;
    case "a-gauche-de": return `est plus à gauche que le ${cible}`;
    case "au-dessus-de": return `est plus haut que le ${cible}`;
    case "en-dessous-de": return `est plus bas que le ${cible}`;
    case "autre-ligne": return `n'est pas sur la même ligne que le ${cible}`;
    case "autre-colonne": return `n'est pas dans la même colonne que le ${cible}`;
    case "si-alors": return `si le ${cible} est dans un coin, alors lui aussi est sur le bord`;
    default: return "";
  }
}

function phraseAtome(atome, n) {
  const position = predicatAtome(atome, n);
  if (!position.texte) return relationAtome(atome, n);
  if (position.negation === "pas") return `n'est pas ${position.texte}`;
  if (position.negation === "ni") return `n'est ni ${position.texte}`;
  return `est ${position.texte}`;
}

function sansEst(texte) {
  return texte.startsWith("est ") ? texte.slice(4) : texte;
}

function libelleCategorie(categorie) {
  if (categorie.figure && categorie.couleur) return `${libelleFigure(categorie.figure)} ${categorie.couleur}`;
  if (categorie.figure) return `pion de forme ${libelleFigure(categorie.figure)}`;
  return `pion de couleur ${categorie.couleur}`;
}

function formaterIndiceCollectif(indice, n) {
  const noms = nomsPour(n);
  const zone = indice.numero === "chaque"
    ? `Chaque ${indice.zone}`
    : `La ${indice.zone} ${(indice.zone === "ligne" ? noms.lignes : noms.colonnes)[indice.numero]}`;
  if (indice.type === "compte-categorie") {
    const categorie = libelleCategorie(indice.categorie);
    if (indice.nombre === 0) return `${zone} ne contient aucun ${categorie}.`;
    // Le nom « pion(s) » évite de pluraliser chaque nom de forme.
    const complement = indice.categorie.figure && indice.categorie.couleur
      ? `de forme ${libelleFigure(indice.categorie.figure)} et de couleur ${indice.categorie.couleur}`
      : indice.categorie.figure
        ? `de forme ${libelleFigure(indice.categorie.figure)}`
        : `de couleur ${indice.categorie.couleur}`;
    return `${zone} contient exactement ${indice.nombre} pion${indice.nombre > 1 ? "s" : ""} ${complement}.`;
  }
  if (indice.type === "diversite") {
    return `${zone} contient exactement un pion de chaque ${indice.attribut === "figure" ? "forme" : "couleur"}.`;
  }
  if (indice.type === "entre") {
    const [a, b] = indice.extremites;
    const extremites = a.figure === b.figure && a.couleur === b.couleur
      ? `deux pions ${a.figure ? `de forme ${libelleFigure(a.figure)}` : ""}${a.figure && a.couleur ? " et " : ""}${a.couleur ? `de couleur ${a.couleur}` : ""}`
      : `un ${libelleCategorie(a)} et un ${libelleCategorie(b)}`;
    const alignement = indice.axe === "ligne" ? "sur une même ligne"
      : indice.axe === "colonne" ? "dans une même colonne" : "sur une même diagonale";
    // En 3×3, trois pions alignés occupent forcément trois cases consécutives.
    // La précision sur les distances ne devient utile que pour une grille plus grande.
    const precision = n > 3 ? ", sans être nécessairement voisins ni à égale distance" : "";
    return `Le ${libelleFigure(indice.figure)} ${indice.couleur} est strictement entre ${extremites}, ${alignement}${precision}.`;
  }
  return null;
}

function formaterEnonce(indice, n) {
  if (["compte-categorie", "diversite", "entre"].includes(indice.type)) {
    return formaterIndiceCollectif(indice, n);
  }
  const atomes = [indice, ...(Array.isArray(indice.et) ? indice.et : [])];
  const nomDe = (atome) =>
    `${libelleFigure(atome.figure || indice.figure)} ${atome.couleur || indice.couleur}`;

  let texte = "";
  let sujet = null;
  let cible = null;
  atomes.forEach((atome, rang) => {
    const ceSujet = `${atome.figure || indice.figure}:${atome.couleur || indice.couleur}`;
    const predicat = phraseAtome(atome, n);
    if (rang === 0) {
      texte += `Le ${nomDe(atome)} ${predicat}`;
    } else if (ceSujet === sujet) {
      texte += ` et ${predicat}`;
    } else if (ceSujet === cible) {
      texte += `, qui ${predicat}`;
    } else {
      texte += `, et le ${nomDe(atome)} ${predicat}`;
    }
    sujet = ceSujet;
    cible = atome.figure2 ? `${atome.figure2}:${atome.couleur2}` : null;
  });
  return texte + ".";
}

function formaterAideRaisonnement(aide, n, niveau) {
  const pion = `${libelleFigure(aide.figure)} ${aide.couleur}`;
  const references = aide.phrases.join(", ");
  const cases = nomsPour(n).cases;
  if (niveau === 0) return `Observe les phrases ${references}. Cherche où peut se trouver le ${pion}. Croise ces informations avant de placer le pion.`;
  if (niveau === 1 && aide.mode === "croisement") {
    const premiere = (aide.demonstration || []).find(e => e.reductions.some(r => r.cases.length > 1));
    const details = premiere ? premiere.reductions.filter(r => r.cases.length > 1).map(r =>
      `${libelleFigure(r.figure)} ${r.couleur} : ${r.cases.map(c => cases[c]).join(" ; ")}.`).join("\n") : "";
    return `Commence par appliquer la phrase ${premiere ? premiere.phrase : aide.phrases[0]}. Compare les possibilités restantes :\n${details}\nReprends ensuite les autres phrases citées : une case déjà occupée ne peut plus accueillir un autre pion.`;
  }
  if (niveau === 1) {
    const details = aide.phrases.map((rang, i) => `Phrase ${rang} : ${aide.possibilites[i].map(c => cases[c]).join(" ; ")}.`).join("\n");
    return `Pour le ${pion}, voici les cases encore possibles en appliquant chaque phrase séparément.\n${details}\n${aide.mode === "intersection" ? "Cherche la case commune à ces listes." : "Il faut aussi croiser les positions des autres pions : chaque case ne reçoit qu’un pion."}`;
  }
  if (aide.mode === "croisement") {
    const trace = aide.demonstration.map(e => `Avec la phrase ${e.phrase} et les possibilités déjà établies :\n` +
      e.reductions.map(r => `${libelleFigure(r.figure)} ${r.couleur} → ${r.cases.map(c => cases[c]).join(" ; ")}.`).join("\n")).join("\n\n");
    return `${trace}\n\nChaque pion et chaque case sont utilisés une fois. Ces éliminations donnent une seule position pour le ${pion} : ${cases[aide.case]}.`;
  }
  return aide.mode === "intersection"
    ? `La seule case commune aux possibilités des phrases ${references} est ${cases[aide.case]}. Le ${pion} y est donc placé : aucune information supplémentaire n’a été ajoutée.`
    : `En croisant les phrases ${references} et en tenant compte des cases occupées par les autres pions, une seule position reste possible pour le ${pion} : ${cases[aide.case]}. Chaque pion est utilisé une seule fois et chaque case reçoit un seul pion.`;
}

function nomsCourtsCases(n) {
  if (n === 4) {
    const noms = [];
    for (let ligne = 1; ligne <= 4; ligne += 1) {
      for (let colonne = 1; colonne <= 4; colonne += 1) noms.push(`L${ligne}C${colonne}`);
    }
    return noms;
  }
  return ["H·G", "H·C", "H·D", "M·G", "M·C", "M·D", "B·G", "B·C", "B·D"];
}

function rendreTableauDeduction(contenu) {
  const n = contenu.figures.length;
  const courts = nomsCourtsCases(n);
  const entete = creerElement("tr", {}, creerElement("th", { attributs: { scope: "col" } }),
    ...courts.map((nom) => creerElement("th", { texte: nom, attributs: { scope: "col" } })));
  const corps = creerElement("tbody");
  for (const couleur of contenu.couleurs) {
    for (const figure of contenu.figures) {
      const ligne = creerElement("tr");
      const titre = creerElement("th", { classe: "tableau-jeton", attributs: { scope: "row" } });
      titre.append(creerElement("span", { texte: GLYPHES[figure], attributs: { "aria-hidden": "true" } }));
      titre.append(creerElement("span", { texte: ` ${couleur}`, classe: "tableau-nom" }));
      titre.style.color = TEINTES[couleur];
      ligne.append(titre);
      for (let c = 0; c < n * n; c += 1) {
        const cellule = creerElement("td", {
          texte: "",
          attributs: {
            role: "button", tabindex: "0",
            "aria-label": `${libelleFigure(figure)} ${couleur} — case ${courts[c]}`,
          },
        });
        const basculer = () => {
          cellule.textContent = cellule.textContent === "" ? "✗" : cellule.textContent === "✗" ? "✓" : "";
          cellule.dataset.etat = cellule.textContent;
          cellule.setAttribute("aria-label", `${libelleFigure(figure)} ${couleur} — case ${courts[c]} — ${cellule.textContent === "✗" ? "impossible" : cellule.textContent === "✓" ? "certain" : "non renseigné"}`);
        };
        cellule.addEventListener("click", basculer);
        cellule.addEventListener("keydown", (evenement) => {
          if (evenement.key === "Enter" || evenement.key === " ") {
            evenement.preventDefault();
            basculer();
          }
        });
        ligne.append(cellule);
      }
      corps.append(ligne);
    }
  }
  const legende = n === 4
    ? "L = ligne (1 = haut), C = colonne (1 = gauche)."
    : "H = haut, M = milieu, B = bas · G = gauche, C = centre, D = droite.";
  return creerElement("details", { classe: "methode-panneau" },
    creerElement("summary", { texte: "Aide — noter les possibilités" }),
    creerElement("p", { classe: "tableau-legende",
      texte: `Ce brouillon facultatif permet de garder les possibilités sous les yeux. Tu peux faire l’exercice sans l’ouvrir. ${legende} Cliquez une case pour la marquer : ✗ impossible, ✓ certain.` }),
    creerElement("div", { classe: "tableau-enveloppe" },
      creerElement("table", { classe: "tableau-deduction" }, creerElement("thead", {}, entete), corps))
  );
}

function rendreGrille(item) {
  const contenu = item.contenu;
  const n = contenu.figures.length;
  etat.grille = Array(n * n).fill(null);
  etat.jetonChoisi = null;

  const plateau = creerElement("div", { classe: "grille-3x3" });
  plateau.style.gridTemplateColumns = `repeat(${n}, 3rem)`;
  plateau.style.gridAutoRows = "3rem";
  const cellules = [];
  for (let c = 0; c < n * n; c++) {
    const bouton = creerElement("button", {
      classe: "cellule",
      attributs: { type: "button", "aria-label": nomsPour(n).cases[c] },
    });
    bouton.addEventListener("click", () => placerCellule(c, bouton));
    plateau.append(bouton);
    cellules.push(bouton);
  }

  const palette = creerElement("div", { classe: "palette", attributs: { "aria-label": "Jetons disponibles" } });
  palette.style.gridTemplateColumns = `repeat(${n}, 2.7rem)`;
  palette.style.gridAutoRows = "2.7rem";
  const jetons = [];
  for (const couleur of contenu.couleurs) {
    for (const figure of contenu.figures) {
      const jeton = creerElement("button", {
        classe: "jeton",
        texte: GLYPHES[figure],
        attributs: {
          type: "button",
          "aria-label": `${libelleFigure(figure)} ${couleur}`,
          "data-jeton": `${figure}:${couleur}`,
          "data-nom": `${libelleFigure(figure)} ${couleur}`,
        },
      });
      jeton.style.color = TEINTES[couleur];
      jeton.addEventListener("click", () => {
        etat.jetonChoisi = `${figure}:${couleur}`;
        for (const j of jetons) j.classList.remove("jeton-actif");
        jeton.classList.add("jeton-actif");
      });
      palette.append(jeton);
      jetons.push(jeton);
    }
  }

  /** Grise les figures déjà posées : un jeton posé n'est plus sélectionnable.
   *  Il redevient disponible dès qu'il est retiré de la grille (clic sur sa case,
   *  ou « Vider la grille »). */
  function rafraichirPalette() {
    const places = new Set(etat.grille.filter(Boolean));
    for (const bouton of jetons) {
      const jeton = bouton.dataset.jeton;
      const pris = places.has(jeton);
      bouton.disabled = pris;
      bouton.classList.toggle("jeton-place", pris);
      bouton.setAttribute("aria-label", pris
        ? `${bouton.dataset.nom} — déjà placé dans la grille`
        : bouton.dataset.nom);
      if (pris) {
        bouton.classList.remove("jeton-actif");
        if (etat.jetonChoisi === jeton) etat.jetonChoisi = null;
      }
    }
  }

  const boutonVider = creerElement("button", {
    classe: "bouton bouton-secondaire",
    texte: "Vider la grille",
    attributs: { type: "button" },
  });
  boutonVider.addEventListener("click", () => {
    etat.grille = Array(n * n).fill(null);
    etat.jetonChoisi = null;
    for (const j of jetons) j.classList.remove("jeton-actif");
    for (const b of cellules) { b.textContent = ""; b.style.color = ""; }
    rafraichirPalette();
  });

  const boutonValider = creerElement("button", {
    classe: "bouton bouton-primaire bouton-large",
    texte: "Valider",
    attributs: { type: "button" },
  });
  boutonValider.addEventListener("click", () => {
    if (etat.grille.every(Boolean)) soumettreGrille();
  });

  const indices = creerElement("ol", { classe: "grille-indices" },
    ...contenu.enonces.map((e) => creerElement("li", { texte: formaterEnonce(e, n) }))
  );

  // Aides graduées ; compatibilité avec les anciens contenus à secours directs.
  let revele = 0;
  const aideRaisonnement = contenu.aide_raisonnement;
  const secours = Array.isArray(contenu.indices) ? contenu.indices : [];
  const listeSecours = creerElement("ul", { classe: "grille-indices grille-secours" });
  const boutonIndice = creerElement("button", {
    classe: "bouton bouton-secondaire",
    texte: aideRaisonnement ? "Aide au raisonnement" : "Un indice",
    attributs: { type: "button" },
  });
  boutonIndice.addEventListener("click", () => {
    if (aideRaisonnement) {
      if (revele >= 3) return;
      const texte = formaterAideRaisonnement(aideRaisonnement, n, revele);
      const paragraphe = creerElement("li", { texte });
      paragraphe.style.whiteSpace = "pre-line";
      listeSecours.append(paragraphe);
      revele += 1;
      boutonIndice.textContent = revele === 1 ? "Comparer les possibilités" : "Voir la conclusion expliquée";
      if (revele === 3) { boutonIndice.disabled = true; boutonIndice.textContent = "Aide affichée"; }
      return;
    }
    if (revele < secours.length) {
      listeSecours.append(creerElement("li", { texte: formaterEnonce(secours[revele], n) }));
      revele += 1;
      if (revele >= secours.length) boutonIndice.disabled = true;
    }
  });
  const zoneIndices = creerElement("div", {},
    contenu.methode_depart ? creerElement("p", { texte: contenu.methode_depart }) : null,
    indices,
    listeSecours,
    (aideRaisonnement || secours.length) ? boutonIndice : null
  );

  refs.zoneGrille.replaceChildren(
    creerElement("div", { classe: "grille-corps" }, plateau, palette),
    zoneIndices,
    rendreTableauDeduction(contenu),
    creerElement("div", { classe: "grille-actions" }, boutonVider, boutonValider)
  );
  refs.zoneGrille.hidden = false;

  rafraichirPalette();

  /** Pose, retire ou remplace un jeton :
   *  - un jeton est sélectionné → on le pose (ou il remplace celui de la case) ;
   *  - aucun jeton sélectionné → un clic sur une case occupée la vide. */
  function placerCellule(c, bouton) {
    const actuel = etat.grille[c];
    if (!etat.jetonChoisi && !actuel) return;
    const jeton = actuel === etat.jetonChoisi ? null : (etat.jetonChoisi || null);
    etat.grille[c] = jeton;
    if (jeton) {
      const [figure, couleur] = jeton.split(":");
      bouton.textContent = GLYPHES[figure];
      bouton.style.color = TEINTES[couleur];
    } else {
      bouton.textContent = "";
      bouton.style.color = "";
    }
    rafraichirPalette();
  }
}

async function soumettreGrille() {
  const chaine = etat.grille.map((cellule) => cellule || "").join(";");
  await soumettreValeur(chaine, null);
}

function rendreFeedbackGrille(resultat) {
  const solution = String(resultat.attendue || "").split(";");
  const n = Math.round(Math.sqrt(solution.length)) || 3;
  refs.carteFeedback.replaceChildren();
  refs.carteFeedback.className =
    "carte-feedback " + (resultat.correcte ? "feedback-correct" : "feedback-incorrect");
  refs.carteFeedback.append(
    creerElement("p", {
      classe: "feedback-titre",
      texte: resultat.correcte ? "✓ Grille exacte !" : "✕ Pas tout à fait",
    })
  );
  const plateau = creerElement("div", { classe: "grille-3x3 grille-solution" });
  plateau.style.gridTemplateColumns = `repeat(${n}, 2.6rem)`;
  plateau.style.gridAutoRows = "2.6rem";
  for (let c = 0; c < solution.length; c++) {
    const cellule = creerElement("div", { classe: "cellule-solution" });
    const [figure, couleur] = (solution[c] || ":").split(":");
    cellule.textContent = GLYPHES[figure] || "";
    cellule.style.color = TEINTES[couleur] || "";
    cellule.classList.add(etat.grille && etat.grille[c] === solution[c] ? "bonne" : "mauvaise");
    plateau.append(cellule);
  }
  refs.carteFeedback.append(plateau);
  refs.carteFeedback.append(
    creerElement("p", { classe: "feedback-commentaire", texte: resultat.feedback })
  );
  refs.carteFeedback.hidden = false;
}

const libelleFigure = (figure) => LIBELLES_FIGURES[figure] || figure;
