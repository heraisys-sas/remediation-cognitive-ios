from dataclasses import dataclass
from .dispatch import corriger
from .sequence import corriger_sequence
from .recall import corriger_rappel_libre


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    correcte: bool
    detail: dict | None = None
    champ: str | None = None

    def feedback(self) -> dict:
        if self.champ is None:
            return {}
        sortie = {self.champ: self.detail}
        if self.champ == "detail_fonctionnel":
            sortie["attendue"] = " ; ".join(
                f"{ligne['label']} : {ligne['attendue']}" for ligne in self.detail['lignes'])
        elif self.champ == "sequence":
            sortie["attendue"] = None
        return sortie


def _fonctionnel(item, reponse):
    from ..attention_fonctionnelle import corriger_detail
    return corriger_detail(item, reponse)


CORRECTEURS_DETAIL = {
    "pqrst-mise-en-oeuvre": (corriger_sequence, "sequence"),
    "rappel-libre": (corriger_rappel_libre, "detail_rappel"),
    **dict.fromkeys(("actualiser-consigne", "comparer-documents", "reperer-essentiel",
                     "reprise-interrompue"), (_fonctionnel, "detail_fonctionnel")),
}


def evaluer(theme: str, item: dict, reponse, assistee: bool = False) -> CorrectionResult:
    correcteur = CORRECTEURS_DETAIL.get(item.get("type"))
    if correcteur:
        fonction, champ = correcteur
        correcte, detail = fonction(item, reponse)
        return CorrectionResult(correcte, detail, champ)
    return CorrectionResult(False if assistee else corriger(theme, item, reponse))
