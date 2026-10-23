"""Orchestration des séances d'entraînement (couche service du sprint 1).

Sépare la logique métier du mapping HTTP (router.py) :
- démarrer une séance : garde-fou de dosage (plafond par thème/catégorie,
  dérogation explicite possible, ADR-021), sélection
  des items (dus FSRS puis nouveaux, max 12), création du
  ``SessionRunner`` (moteur engine/ réutilisé tel quel) ;
- enregistrer une réponse : correction serveur (la réponse attendue ne
  fuit jamais avant soumission), feedback immédiat guidé ;
- terminer la séance : application de FSRS + critère de maîtrise
  (90 % × 3 séances consécutives → palier +1), puis persistance JSON.

Les séances en cours vivent en mémoire (registre) ; seuls les états
cartes / maîtrise / compteur sont persistés à la fin ; les observations
de protocole sont journalisées séparément dès leur validation.
La fatigue (``SessionRunner.doit_proposer_arret``) n'est qu'une
proposition renvoyée en fin de séance — JAMAIS une interruption.
"""

from __future__ import annotations

import re
import copy
import statistics
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from engine.session.runner import SessionRunner
from engine.srs.fsrs import CarteFSRS, planifier

from ...domain import messages
from ...domain.contenu import ChargeurContenu
from ...domain.correction import corriger, evaluer
from ...domain.feedback import essai_supplementaire
from ...domain.dosage import (
    MAX_REPRISES_PAR_SEANCE,
    debut_fenetre,
    duree_proposee,
    fenetre_sessions,
    limite_sessions_theme,
    parametres_seance,
)
from ...domain.selection import selectionner_items
from ...domain.observations_contextes import normaliser_faits, fusionner_faits
from ...storage.store import StockageJSON

# Notes FSRS v1 : réussite → Good (3), échec → Again (1).
NOTE_REUSSITE = 3
NOTE_ECHEC = 1

from ...domain.progression import (
    progression_apres_session, PALIER_DEPART_CALCUL, SEUIL_REPLI_CALCUL,
)


def _horloge_utc() -> datetime:
    return datetime.now(timezone.utc)


# -- exceptions métier (le router les mappe vers les codes du contrat) ---------


class ThemeInconnu(Exception):
    """Thème absent du registre de l'API."""


class LimiteSessionsAtteinte(Exception):
    """Garde-fou de dosage : quota journalier de séances déjà consommé."""

    def __init__(self, restantes: int = 0) -> None:
        super().__init__(restantes)
        self.restantes = restantes


class SessionInconnue(Exception):
    """Identifiant de séance inconnu (ou thème ne correspondant pas)."""


class SessionDejaTerminee(Exception):
    """La séance a déjà été clôturée (409 du contrat)."""


class PalierInconnu(Exception):
    """Palier demandé absent du thème (essai)."""


class ParcoursInconnu(Exception):
    """Parcours demandé absent du thème."""


class ItemHorsSeance(Exception):
    """Item absent de la séance en cours (404 du contrat)."""


class ReponseInvalide(Exception):
    """Réponse ou temps invalide (422)."""


# -- adaptations locales -------------------------------------------------------


class ItemMoteur:
    """Adapte un item de contenu au contrat du moteur (attribut ``item_id``).

    engine.session.runner attend des items exposant ``item_id`` ; le
    contenu versionné utilise la clé ``id``. L'adaptation reste côté
    backend : engine/ n'est pas modifié.
    """

    def __init__(self, item: dict) -> None:
        self.item = item
        self.item_id = item["id"]


@dataclass
class SessionEnCours:
    """État serveur d'une séance démarrée (en mémoire jusqu'à la fin)."""

    session_id: str
    theme: str
    stockage_theme: str
    parcours: str | None
    palier: int
    palier_force: bool
    runner: SessionRunner
    items_par_id: dict[str, dict]
    items_disponibles: list[dict]
    # Départ de la séance (garde-fou de durée, injectable via l'horloge).
    depart: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Première réponse par item — fait foi pour FSRS ; les essais
    # supplémentaires (reprises errorless) restent comptés par le moteur.
    reponses: dict[str, bool] = field(default_factory=dict)
    # Temps (ms) des premières réponses correctes — baseline RT adaptative.
    temps_reference: list[float] = field(default_factory=list)
    protocoles_pqrst: set[str] = field(default_factory=set)
    # Indices consultés par item (0 = sans aide) — mesure de l'aide nécessaire.
    indices_utilises: dict[str, int] = field(default_factory=dict)
    # Exercices déjà repris en fin de séance (un échec = au plus une reprise).
    reprises: set[str] = field(default_factory=set)
    # Nombre d'essais par item : le second essai des exercices de stratégie en dépend.
    essais: dict[str, int] = field(default_factory=dict)
    # Payload de fin conservé pour rendre la clôture idempotente.
    resume_cloture: dict | None = None
    # Arrêt déjà proposé pour cause de durée (proposition envoyée une seule fois).
    arret_propose_envoye: bool = False
    # Essais clos en affichant la réponse : aucune erreur commise par
    # l'utilisateur, mais pas de récupération réussie non plus.
    assistees: set[str] = field(default_factory=set)
    protocole_contextes: dict | None = None
    items_decouverts: set[str] = field(default_factory=set)
    terminee: bool = False


def _item_sans_reponse(item: dict) -> dict:
    """Payload client d'un item : id/type/palier/contenu — JAMAIS ``reponse``."""
    return {
        "id": item["id"],
        "type": item["type"],
        "palier": item["palier"],
        "contenu": ({**item["contenu"], "interface_pqrst": messages.PQRST_INTERFACE}
                    if item["type"] == "pqrst-mise-en-oeuvre" else item["contenu"]),
    }


class GestionnaireSessions:
    """Point d'entrée métier : démarrer / répondre / terminer une séance."""

    def __init__(
        self,
        stockage: StockageJSON | None = None,
        contenu: ChargeurContenu | None = None,
        horloge: Callable[[], datetime] | None = None,
    ) -> None:
        self.stockage = stockage or StockageJSON()
        self.contenu = contenu or ChargeurContenu()
        # Horloge injectable (tests) — horloge UTC réelle par défaut.
        self.horloge = horloge or _horloge_utc
        self._sessions: dict[str, SessionEnCours] = {}
        # Sérialise lecture → incrément → écriture du compteur journalier.
        self._verrou_dosage = threading.Lock()

    # -- démarrage -----------------------------------------------------------

    def demarrer(
        self,
        theme: str,
        palier_force: int | None = None,
        sans_limite_sessions: bool = False,
        parcours: str | None = None,
        rejouer_palier: bool = False,
        profil_contextes: str | None = None,
    ) -> dict:
        """Démarre une séance et retourne le payload 201 du contrat.

        ``palier_force`` (essai) : travaille un palier choisi au lieu du palier courant.
        La **maîtrise n'est pas modifiée en mal** par ce choix : le critère de progression
        n'avance que vers le haut (``max(palier, session.palier + 1)``), donc un palier
        forcé ne peut pas faire reculer la progression — au mieux la fait-il avancer si la
        personne réussit, ce qui est exact.

        ``rejouer_palier`` : complète la sélection avec les exercices déjà vus
        non dus du palier choisi, sans réinitialiser les cartes ni la progression.

        ``sans_limite_sessions`` (dérogation, ADR-021) : la personne demande à
        dépasser le plafond de sa fenêtre (jour, ou semaine pour l'évaluation) ;
        accordée pour tous les thèmes ; le compteur continue de compter la séance.

        Lève ``ThemeInconnu`` (404), ``PalierInconnu`` (422) ou
        ``LimiteSessionsAtteinte`` (429). Le compteur du jour est incrémenté dès le
        démarrage (une séance entamée compte dans le dosage, qu'elle aille à son terme
        ou non).
        """
        if not self.contenu.theme_existe(theme):
            raise ThemeInconnu(theme)
        if not self.contenu.parcours_existe(theme, parcours):
            raise ParcoursInconnu(parcours)
        if profil_contextes is not None and (profil_contextes not in ("origine", "sources-vues") or (theme, parcours) != ("evocation", "memoire-source")):
            raise ReponseInvalide("profil_contextes incompatible")
        protocole = ({"version": "contextes-source-v2", "profil": profil_contextes or "origine"}
                     if (theme, parcours) == ("evocation", "memoire-source") else None)
        stockage_theme = f"{theme}--{parcours}" if parcours else theme
        items_disponibles = self.contenu.items(theme, parcours)
        categorie = self.contenu.categorie(theme)
        reglages = parametres_seance(theme)
        limite = limite_sessions_theme(theme, categorie)
        fenetre = fenetre_sessions(categorie)
        # Dérogation explicite (ADR-021) : elle couvre tous les thèmes — la règle
        # reste côté serveur, l'interface la demande, elle ne la contourne pas.
        deroge = sans_limite_sessions
        with self._verrou_dosage, self.stockage.transaction_theme(theme):
            maintenant = self.horloge()
            debut = debut_fenetre(fenetre, maintenant.date())
            nb_sessions = self.stockage.lire_compteur(theme, debut)
            if not deroge and nb_sessions >= limite:
                raise LimiteSessionsAtteinte(
                    restantes=max(0, limite - nb_sessions)
                )
            etat_maitrise = self.stockage.lire_maitrise(stockage_theme)
            if palier_force is not None and palier_force not in self.contenu.paliers(theme, parcours):
                raise PalierInconnu(palier_force)
            progression_neuve = not self.stockage.maitrise_existe(stockage_theme)
            palier_initial = (
                self.contenu.palier_depart(theme, parcours)
                if progression_neuve else etat_maitrise["palier_courant"]
            )
            # Compatibilité avec les progressions créées avant le relèvement du
            # départ : une réussite récente au socle permet de rejoindre le nouveau
            # point d'entrée ; une difficulté (< 50 %) conserve le niveau stocké.
            if (
                theme == "calcul-mental"
                and parcours is None
                and palier_initial < PALIER_DEPART_CALCUL
                and (
                    not etat_maitrise["historique"]
                    or etat_maitrise["historique"][-1][1] >= SEUIL_REPLI_CALCUL
                )
            ):
                palier_initial = PALIER_DEPART_CALCUL
            palier = palier_force if palier_force is not None else self._palier_courant(
                theme, palier_initial, parcours
            )
            if palier_force is None and (
                progression_neuve or palier_initial != etat_maitrise["palier_courant"]
            ):
                # Le départ relevé devient l'état réel : une première séance
                # interrompue ne doit pas faire retomber la progression au palier 1.
                self.stockage.ecrire_maitrise(
                    stockage_theme,
                    palier,
                    list(etat_maitrise["historique"]),
                    etat_maitrise.get("historique_etapes"),
                )
            quota_parcours = self.contenu.max_items_parcours(theme, parcours, palier)
            if quota_parcours is not None:
                reglages = {**reglages, "max_items": quota_parcours}
            cartes = self.stockage.lire_cartes(stockage_theme)
            # Dosage propre au thème : une grille de déduction n'a pas le coût
            # d'un item de calcul mental (voir domain/dosage.parametres_seance).
            selection = selectionner_items(
                items_disponibles,
                cartes,
                palier,
                maintenant,
                reglages["max_items"],
                inclure_non_dus=rejouer_palier or bool(reglages.get("inclure_non_dus", False)),
            )
            selection = copy.deepcopy(selection)
            if protocole and protocole["profil"] == "sources-vues":
                sources = list(dict.fromkeys(item["reponse"]["valeur"] for item in selection))
                for index, item in enumerate(selection):
                    correcte = item["reponse"]["valeur"]
                    candidates = [source for source in sources if source != correcte]
                    rotation = index % max(1, len(candidates))
                    autres = (candidates[rotation:] + candidates[:rotation])[:3]
                    choix = autres[:]
                    choix.insert(index % (len(autres) + 1), correcte)
                    # Une seule liste par condition : deux listes différentes
                    # révéleraient parfois la réponse par leur intersection.
                    item["contenu"]["options"] = choix.copy()
                    item["contenu"]["options_rappel"] = choix
            runner = SessionRunner(
                items=[ItemMoteur(item) for item in selection],
                max_items=reglages["max_items"],
                duree_max_s=reglages["duree_max_s"],
                baseline_rt_ms=self._baseline_rt(stockage_theme),
                depart=maintenant,
            )
            # Le contrat livre tous les items d'un bloc au démarrage : ils
            # sont donc tous « servis » dès l'ouverture de la séance, et le
            # moteur peut ensuite enregistrer chaque réponse.
            while runner.prochain_item() is not None:
                pass
            session_id = str(uuid.uuid4())
            self._sessions[session_id] = SessionEnCours(
                session_id=session_id,
                theme=theme,
                stockage_theme=stockage_theme,
                parcours=parcours,
                palier=palier,
                palier_force=palier_force is not None,
                runner=runner,
                items_par_id={item["id"]: item for item in selection},
                items_disponibles=items_disponibles,
                depart=maintenant,
                protocole_contextes=protocole,
            )
            # Une séance **vide** (rien de dû, rien de nouveau) ne consomme pas le quota
            # de la fenêtre : elle n'a rien proposé, elle ne doit rien coûter.
            if selection:
                self.stockage.incrementer_compteur(theme, debut)
        if protocole:
            self.stockage.modifier_observations(session_id, lambda document: {**document, "protocole_contextes": protocole.copy()})
        return {
            "session_id": session_id,
            "parcours": parcours,
            **({"protocole_contextes": protocole} if protocole else {}),
            "items": [_item_sans_reponse(item) for item in selection],
            "regles": {
                "max_items": reglages["max_items"],
                "duree_max_s": reglages["duree_max_s"],
            },
        }

    def _palier_courant(
        self, theme: str, palier_stocke: int, parcours: str | None = None
    ) -> int:
        """Palier de travail : celui du stockage, borné au contenu disponible."""
        paliers = self.contenu.paliers(theme, parcours)
        if not paliers:
            return max(1, palier_stocke)
        return min(max(1, palier_stocke), paliers[-1])

    def _baseline_rt(self, theme: str) -> float:
        """Baseline RT adaptative : médiane des dernières réponses correctes.

        Revue exécution : une baseline figée à 1000 ms produit de faux
        positifs de fatigue chez les utilisateurs lents. On prend la
        médiane des ≤ 100 derniers temps corrects persistés ; 1000 ms
        tant que l'échantillon est trop petit (moins de 5 réponses).
        """
        temps = self.stockage.lire_temps_reference(theme)
        if len(temps) >= 5:
            return float(statistics.median(temps))
        return 1000.0

    # -- réponses ------------------------------------------------------------

    def verifier_dictee(self, theme: str, session_id: str, item_id: str,
                        transcription: str) -> dict:
        """Prévisualise un mot dicté sans essai, feedback ni écriture persistante.

        Seul le rappel lexical libre autorise cette détection automatique. Les
        transcriptions intermédiaires négatives restent sans effet sur la séance.
        """
        session = self._session(theme, session_id)
        if session.terminee:
            raise SessionDejaTerminee()
        item = session.items_par_id.get(item_id)
        if item is None:
            raise ItemHorsSeance()
        if (theme != "evocation" or item.get("type") != "rappel-indice"
                or not isinstance(transcription, str) or len(transcription) > 500):
            raise ReponseInvalide()
        # Une transcription « ce n'est pas une gare » contient le bon mot,
        # mais ne doit jamais déclencher une validation automatique.
        negation = re.search(r"\b(?:pas|jamais|sans|aucun|aucune|non|ni)\b",
                             transcription, flags=re.IGNORECASE)
        return {"acceptee": not bool(negation) and corriger(theme, item, transcription)}

    def repondre(
        self,
        theme: str,
        session_id: str,
        item_id: str,
        reponse,
        temps_ms,
        indice_utilise: int | None = None,
        memorisation: bool = False,
        observation_contextes: dict | None = None,
    ) -> dict:
        """Corrige côté serveur et retourne le payload 200 du contrat.

        ``indice_utilise`` (optionnel, 0 par défaut) : nombre d'indices
        consultés par l'utilisateur. La valeur ``nb_indices + 1`` signale que
        la réponse a été AFFICHÉE — l'essai est alors « assisté » : aucune
        erreur n'est commise (principe errorless) mais la récupération n'a pas
        eu lieu, donc la carte FSRS est notée en échec et le taux de réussite
        ne la compte pas comme réussite.

        Lève ``SessionInconnue`` (404), ``SessionDejaTerminee`` (409),
        ``ItemHorsSeance`` (404) ou ``ReponseInvalide`` (422).
        """
        session = self._session(theme, session_id)
        if session.terminee:
            raise SessionDejaTerminee()
        item = session.items_par_id.get(item_id)
        if item is None:
            raise ItemHorsSeance()
        # Garde-fou de dosage : au-delà de la durée maximale, la séance s'arrête —
        # mais la réponse en cours est **conservée**. Une personne qui a travaillé
        # ne doit pas voir son travail refusé parce que la limite est tombée
        # pendant qu'elle répondait ; le client est prévenu pour proposer le résumé.
        duree_depassee = (
            (self.horloge() - session.depart).total_seconds()
            >= session.runner.duree_max_s
        )
        nb_indices = len((item.get("contenu") or {}).get("indices") or [])
        if indice_utilise is None:
            indice_utilise = 0
        if (
            isinstance(indice_utilise, bool)
            or not isinstance(indice_utilise, int)
            or indice_utilise < 0
            or indice_utilise > nb_indices + 1
        ):
            raise ReponseInvalide("indice_utilise hors bornes")
        assistee = nb_indices > 0 and indice_utilise > nb_indices
        if session.protocole_contextes and session.protocole_contextes["profil"] == "sources-vues" and not memorisation:
            if set(session.items_par_id) != session.items_decouverts:
                raise ReponseInvalide("sources proposées non découvertes")
        if (session.protocole_contextes and session.protocole_contextes["profil"] == "sources-vues"
                and observation_contextes is None):
            raise ReponseInvalide("observation de passe requise")
        faits = None
        if observation_contextes is not None:
            try:
                if observation_contextes.get("photo_apres_erreur") or "photo_revelee_ms" in observation_contextes:
                    raise ValueError("révélation avant correction")
                faits = self._faits_contexte(session, item, observation_contextes)
                if session.protocole_contextes and (faits["passe"] == "decouverte") != memorisation:
                    raise ValueError("passe incompatible avec memorisation")
                if faits["passe"] == "rappel" and not any(
                    ligne["item_id"] == item_id and ligne.get("premiere_reponse")
                    for ligne in self.stockage.lire_observations(session_id).get("contextes", {}).get("decouverte", [])
                ):
                    raise ValueError("rappel avant découverte")
            except ValueError as exc:
                raise ReponseInvalide(str(exc)) from exc
        if session.protocole_contextes and session.protocole_contextes["profil"] == "sources-vues" and memorisation:
            if not faits or not faits.get("photo_chargee") or "exposition_ms" not in faits:
                raise ReponseInvalide("photo non exposée")
        try:
            correction = evaluer(theme, item, reponse, assistee)
        except ValueError as exc:
            raise ReponseInvalide(str(exc)) from exc
        correcte = correction.correcte

        # Scènes de contexte : la découverte prépare l’encodage. Seul le rappel
        # final doit alimenter le moteur, la maîtrise, FSRS et les temps de référence.
        if memorisation:
            if (theme != "evocation" or item.get("type") != "rappel-source"
                    or not item.get("contenu", {}).get("affichage", {}).get("image")
                    or item_id in session.reponses):
                raise ReponseInvalide("memorisation hors parcours ou après rappel")
            if isinstance(temps_ms, bool) or not isinstance(temps_ms, (int, float)) or temps_ms < 0:
                raise ReponseInvalide("temps_ms hors bornes")
            resultat = {
                "correcte": correcte,
                "assistee": assistee,
                "attendue": item["reponse"]["valeur"],
                "memorisation": True,
                "feedback": messages.texte("entrainement", "feedback_correcte" if correcte else "feedback_incorrecte"),
            }
            resultat.update(correction.feedback())
            session.items_decouverts.add(item_id)
            if faits is not None:
                premiere = {"reponse": reponse, "correcte": correcte, "aide": indice_utilise,
                            "temps_ms": temps_ms, "validee_ms": int(self.horloge().timestamp() * 1000)}
                self._enregistrer_contexte(session, faits, premiere)
            if duree_depassee:
                resultat.update(arret_propose=True, motif_arret="duree")
            return resultat

        # Second essai (exercices où la réponse se **raisonne**, ADR-014) : sur une
        # première erreur, on ne révèle rien et on n'enregistre rien — le premier essai
        # raté ne devient pas la réponse de l'exercice, et c'est l'essai lui-même qui
        # fait apprendre (pratique de récupération).
        tentatives = session.essais.get(item_id, 0) + 1
        session.essais[item_id] = tentatives
        if (tentatives == 1 and not correcte and not assistee
                and essai_supplementaire(item.get("type", ""))):
            return {
                "correcte": False,
                "assistee": False,
                "attendue": None,
                "essai_supplementaire": True,
                "feedback": messages.texte("entrainement", "feedback_essaie_encore"),
            }

        try:
            session.runner.enregistrer_reponse(item_id, correcte, temps_ms)
        except ValueError as exc:
            raise ReponseInvalide(str(exc)) from exc
        if isinstance(reponse, dict) and "_pqrst" in reponse:
            session.protocoles_pqrst.add(item_id)
        premiere_reponse = item_id not in session.reponses
        session.reponses.setdefault(item_id, correcte)
        if premiere_reponse:
            session.indices_utilises[item_id] = indice_utilise
            if assistee:
                session.assistees.add(item_id)
            elif correcte and indice_utilise == 0 and item_id not in session.protocoles_pqrst:
                # Seules les premières réponses correctes SANS AIDE nourrissent
                # la baseline RT (les essais aidés ou dupliqués la fausseraient).
                session.temps_reference.append(float(temps_ms))
        if assistee:
            cle = "feedback_assiste"
        else:
            cle = "feedback_correcte" if correcte else "feedback_incorrecte"
        resultat = {
            "correcte": correcte,
            "assistee": assistee,
            "attendue": item["reponse"]["valeur"],
            "feedback": messages.texte("entrainement", cle),
        }
        resultat.update(correction.feedback())
        if faits is not None:
            premiere = {"reponse": reponse, "correcte": correcte, "aide": indice_utilise,
                        "temps_ms": temps_ms, "validee_ms": int(self.horloge().timestamp() * 1000)}
            self._enregistrer_contexte(session, faits, premiere)
        observation_pqrst = resultat.get("sequence", {}).get("observation")
        if observation_pqrst is not None:
            self._enregistrer_pqrst(session, item_id, observation_pqrst)
        # Reprise errorless : un exercice manqué (et non assisté) revient **une fois**, en
        # fin de séance, avec la réponse fournie avant le nouvel essai. On ne ré-encode pas
        # une erreur ; le plafond évite de doubler la durée de la séance.
        if (not correcte and not assistee and premiere_reponse
                and item_id not in session.reprises
                and len(session.reprises) < MAX_REPRISES_PAR_SEANCE):
            session.reprises.add(item_id)
            resultat["reprise"] = True
        if duree_depassee:
            if duree_proposee(theme):
                # Ce thème traite la durée comme une **proposition** : la séance ne se
                # ferme pas, elle invite à s'arrêter — une seule fois, la personne décide.
                if not session.arret_propose_envoye:
                    session.arret_propose_envoye = True
                    resultat["arret_propose"] = True
                    resultat["motif_arret"] = "duree"
            else:
                # Ailleurs, la durée reste le garde-fou : on enregistre la réponse
                # (**on ne jette jamais le travail fait**) puis la séance se clôt.
                resume_moteur, nb_repondu, nb_correctes, taux = self._cloturer(
                    session, self.horloge()
                )
                session.resume_cloture = self._payload_fin(
                    theme, session, resume_moteur, nb_repondu, nb_correctes, taux
                )
                resultat["seance_terminee"] = True
                resultat["motif"] = "duree"
        return resultat

    def observer(self, theme: str, session_id: str, item_id: str, reponse: dict) -> dict:
        from ...domain.correction.sequence import normaliser_observation_pqrst
        session = self._session(theme, session_id)
        if session.terminee:
            raise SessionDejaTerminee()
        item = session.items_par_id.get(item_id)
        if item is None:
            raise ItemHorsSeance()
        if item["type"] != "pqrst-mise-en-oeuvre":
            raise ReponseInvalide("observation incompatible")
        try:
            observation = normaliser_observation_pqrst(item, reponse, partielle=True)
        except ValueError as exc:
            raise ReponseInvalide(str(exc)) from exc
        self._enregistrer_pqrst(session, item_id, observation)
        return {"enregistree": True}

    def _faits_contexte(self, session: SessionEnCours, item: dict, donnees: dict) -> dict:
        ordre = list(session.items_par_id).index(item["id"]) + 1
        faits = normaliser_faits(item, donnees, ordre)
        if session.protocole_contextes:
            faits["protocole"] = session.protocole_contextes.copy()
            cle = "options_rappel" if faits["passe"] == "rappel" else "options"
            faits["choix_proposes"] = list(item["contenu"].get(cle, item["contenu"].get("options", [])))
        return faits

    def _enregistrer_contexte(self, session: SessionEnCours, faits: dict, premiere: dict | None = None) -> dict:
        def modifier(document):
            lignes = document["contextes"][faits["passe"]]
            ligne = next((ligne for ligne in lignes if ligne["item_id"] == faits["item_id"]), None)
            if ligne is None:
                ligne = {"item_id": faits["item_id"], "passe": faits["passe"], "ordre": faits["ordre"]}
                lignes.append(ligne)
            if premiere is not None:
                ligne.setdefault("premiere_reponse", premiere)
                ligne["presentee"] = True
            fusionner_faits(ligne, faits)
            return document
        return self.stockage.modifier_observations(session.session_id, modifier)

    def _fusionner_contextes(self, session: SessionEnCours, donnees: dict) -> None:
        try:
            if not isinstance(donnees, dict) or set(donnees) - {"decouverte", "rappel"}:
                raise ValueError("passes invalides")
            faits = []
            for passe, lignes in donnees.items():
                if not isinstance(lignes, list) or len(lignes) > len(session.items_par_id):
                    raise ValueError("observations trop nombreuses")
                for ligne in lignes:
                    if not isinstance(ligne, dict) or ligne.get("passe") != passe:
                        raise ValueError("passe incompatible")
                    item = session.items_par_id.get(ligne.get("item_id"))
                    if item is None:
                        raise ValueError("item inconnu")
                    faits.append(self._faits_contexte(session, item, ligne))
            if len({(fait["passe"], fait["item_id"]) for fait in faits}) != len(faits):
                raise ValueError("observations dupliquées")
            def modifier(document):
                for fait in faits:
                    lignes = document["contextes"][fait["passe"]]
                    observation = next((ligne for ligne in lignes if ligne["item_id"] == fait["item_id"]), None)
                    if observation is None:
                        observation = {"item_id": fait["item_id"], "passe": fait["passe"], "ordre": fait["ordre"]}
                        lignes.append(observation)
                    if fait["passe"] == "rappel" and not any(
                        ligne["item_id"] == fait["item_id"] and ligne.get("premiere_reponse")
                        for ligne in document["contextes"]["decouverte"]
                    ):
                        raise ValueError("rappel avant découverte")
                    fusionner_faits(observation, fait)
                return document
            self.stockage.modifier_observations(session.session_id, modifier)
        except ValueError as exc:
            raise ReponseInvalide(str(exc)) from exc

    def _enregistrer_pqrst(self, session: SessionEnCours, item_id: str, observation: dict) -> None:
        def modifier(document):
            precedente = document["pqrst"].get(item_id)
            if not precedente or precedente.get("statut") != "complete":
                document["pqrst"][item_id] = observation
            return document
        self.stockage.modifier_observations(session.session_id, modifier)

    # -- fin de séance ---------------------------------------------------------

    def terminer(self, theme: str, session_id: str, observations_contextes: dict | None = None) -> dict:
        """Clôture la séance : FSRS + maîtrise + persistance, payload 200 du contrat.

        **Idempotent** : un second appel (double clic, ou reprise après la clôture
        automatique par la durée maximale) renvoie le même résumé au lieu d'un
        conflit — le client doit pouvoir afficher le résumé dans tous les cas.
        Lève ``SessionInconnue`` (404) seulement.
        """
        session = self._session(theme, session_id)
        if observations_contextes is not None:
            self._fusionner_contextes(session, observations_contextes)
        if session.terminee:
            if session.resume_cloture is not None:
                if any(item["type"] == "rappel-source" for item in session.items_par_id.values()):
                    session.resume_cloture["observations_contextes"] = self.stockage.lire_observations(session_id).get("contextes", {"decouverte": [], "rappel": []})
                return session.resume_cloture
            raise SessionDejaTerminee()
        resume_moteur, nb_repondu, nb_correctes, taux = self._cloturer(
            session, self.horloge()
        )
        retour = self._payload_fin(theme, session, resume_moteur,
                                   nb_repondu, nb_correctes, taux)
        session.resume_cloture = retour
        return retour

    def _payload_fin(self, theme: str, session: SessionEnCours, resume_moteur: dict,
                     nb_repondu: int, nb_correctes: int, taux: float) -> dict:
        """Payload de fin de séance (résumé, arrêt proposé, quota de la fenêtre)."""
        categorie = self.contenu.categorie(theme)
        fenetre = fenetre_sessions(categorie)
        debut = debut_fenetre(fenetre, self.horloge().date())
        restantes = max(
            0,
            limite_sessions_theme(theme, categorie)
            - self.stockage.lire_compteur(theme, debut),
        )
        arret_propose = bool(resume_moteur["alerte_fatigue"])
        retour = {
            "resume": {
                "items": nb_repondu,
                "correctes": nb_correctes,
                "duree_s": int(round(resume_moteur["duree_s"])),
                "taux_reussite": taux,
            },
            "arret_propose": arret_propose,
            "motif_arret": "fatigue" if arret_propose else None,
            "sessions_restantes_aujourdhui": restantes,
            "fenetre_sessions": fenetre,
        }
        # Champs propres aux exercices d'accès au mot : aide réellement
        # nécessaire et essais clos sans erreur (réponse affichée).
        if session.indices_utilises or session.assistees:
            retour["resume"]["assistees"] = len(session.assistees)
            retour["resume"]["sans_aide"] = sum(
                1
                for item_id, correcte in session.reponses.items()
                if correcte and session.indices_utilises.get(item_id, 0) == 0
                and item_id not in session.protocoles_pqrst
            )
        if any(item["type"] == "rappel-source" for item in session.items_par_id.values()):
            retour["observations_contextes"] = self.stockage.lire_observations(session.session_id).get("contextes", {"decouverte": [], "rappel": []})
        return retour

    def _cloturer(
        self, session: SessionEnCours, maintenant: datetime
    ) -> tuple[dict, int, int, float]:
        # Couvre la lecture-modification-écriture de toutes les progressions.
        with self.stockage.transaction_theme(session.theme):
            return self._cloturer_sous_verrou(session, maintenant)

    def _cloturer_sous_verrou(
        self, session: SessionEnCours, maintenant: datetime
    ) -> tuple[dict, int, int, float]:
        """Finalise la séance : FSRS + maîtrise + baseline RT + persistance.

        Utilisée par la clôture explicite (``terminer``) ET par le
        garde-fou de durée (auto-clôture au-delà de ``duree_max_s``).
        Résumé du contrat : items RÉPONDUS (pas seulement servis) — une
        séance abandonnée en cours de route reste cohérente ; les essais
        dupliqués ne comptent pas (première réponse par item, fait foi).
        """
        resume_moteur = session.runner.terminer()
        self._appliquer_fsrs(session, maintenant)
        nb_repondu = len(session.reponses)
        nb_correctes = sum(1 for correcte in session.reponses.values() if correcte)
        taux = nb_correctes / nb_repondu if nb_repondu else 0.0
        self._appliquer_maitrise(session, nb_repondu, taux)
        # Baseline RT : on accumule les temps corrects de la séance.
        temps_accumules = self.stockage.lire_temps_reference(session.stockage_theme)
        temps_accumules.extend(session.temps_reference)
        self.stockage.ecrire_temps_reference(session.stockage_theme, temps_accumules[-100:])
        session.terminee = True
        return resume_moteur, nb_repondu, nb_correctes, taux

    # -- interne ---------------------------------------------------------------

    def _session(self, theme: str, session_id: str) -> SessionEnCours:
        """Retrouve une séance en mémoire ; thème et identifiant doivent coïncider."""
        session = self._sessions.get(session_id)
        if session is None or session.theme != theme:
            raise SessionInconnue(session_id)
        return session

    def _appliquer_fsrs(self, session: SessionEnCours, maintenant: datetime) -> None:
        """Met à jour les cartes FSRS des items répondus puis persiste le deck."""
        if not session.reponses:
            return
        cartes = self.stockage.lire_cartes(session.stockage_theme)
        for item_id, correcte in session.reponses.items():
            carte = cartes.get(item_id) or CarteFSRS(item_id)
            note = NOTE_REUSSITE if correcte else NOTE_ECHEC
            cartes[item_id] = planifier(carte, note, maintenant)[0]
        self.stockage.ecrire_cartes(session.stockage_theme, cartes)

    def _appliquer_maitrise(self, session: SessionEnCours, nb_repondu: int, taux: float) -> None:
        progression = progression_apres_session(
            session, nb_repondu, taux, self.stockage.lire_maitrise(session.stockage_theme))
        if progression is not None:
            self.stockage.ecrire_maitrise(session.stockage_theme, *progression)
