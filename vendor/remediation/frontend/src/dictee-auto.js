/* Écoute lexicale : les hypothèses de transcription ne sont pas des essais. */
const DicteeAuto = (() => {
  function demarrer({ capacites, verifier, afficher, valider, statut, clavier }) {
    let actif = true, micro = null, desabonner = null, ouverture, controle;
    let version = 0, texte = "", dernier = "", prepare = false;
    function interrompre() {
      version++;
      clearTimeout(ouverture); clearTimeout(controle);
      micro?.abort(); micro = null; prepare = false;
    }
    function abort() {
      actif = false; interrompre(); desabonner?.();
    }
    function manuel() { abort(); afficher(""); clavier(); }
    async function examiner(candidat, revision) {
      try {
        const resultat = await verifier(candidat);
        if (!actif || revision !== version || texte !== candidat) return;
        if (resultat.acceptee) { abort(); valider(candidat); }
      } catch { if (actif && revision === version) { abort(); statut("Vérification indisponible — réponds au clavier"); clavier(false); } }
    }
    function recevoir(valeur) {
      if (!actif) return;
      texte = valeur.trim(); afficher(valeur);
      if (!texte || texte === dernier) return;
      dernier = texte;
      const revision = ++version;
      clearTimeout(controle);
      // Laisser une hypothèse se stabiliser avant la soumission définitive.
      controle = setTimeout(() => examiner(texte, revision), 700);
    }
    function callbacks() {
      return {
        onDebut: () => { if (actif) statut("Parle maintenant · Répondre au clavier"); },
        onPartiel: recevoir, onResultat: recevoir,
        onFin: () => { micro = null; if (actif) statut("Répondre au clavier"); },
        onErreur: () => { if (actif) { abort(); clavier(false); statut("Micro indisponible — réponds au clavier"); } },
      };
    }
    function lecture(active) {
      if (!actif) return;
      clearTimeout(ouverture);
      if (active) {
        // La synthèse native émet plusieurs transitions pendant sa préparation.
        // Garder le micro déjà préparé, au lieu de le rouvrir à chacune.
        if (!prepare) {
          interrompre(); dernier = "";
          micro = capacites.preparerDictee?.(callbacks()) || null;
          prepare = Boolean(micro);
        }
        statut("Après la lecture · Répondre au clavier");
        return;
      }
      ouverture = setTimeout(() => {
        if (!actif || capacites.lectureEnCours()) return;
        statut("Préparation du micro · Répondre au clavier");
        if (prepare) { prepare = false; micro.activer(); }
        else if (!micro) micro = capacites.dicter(callbacks());
      }, 150);
    }
    desabonner = capacites.observerLecture(lecture);
    return { abort, stop: manuel, manuel };
  }
  return { demarrer };
})();
