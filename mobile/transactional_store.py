"""Stockage SQLite du pilote : formats JSON métier conservés, validation atomique."""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

from backend.app.storage.store import StockageJSON


class TransactionalStore(StockageJSON):
    def __init__(self, root: Path):
        super().__init__(root)
        root.mkdir(parents=True, exist_ok=True)
        # Les appels sont sérialisés mais une file GCD peut changer de thread.
        self.connection = sqlite3.connect(root / "pilot.sqlite", isolation_level=None, check_same_thread=False)
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute("CREATE TABLE IF NOT EXISTS documents (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

    @contextmanager
    def transaction_theme(self, theme):
        # L'appel natif englobe déjà correction, progression et checkpoint.
        if self.connection.in_transaction:
            yield
        else:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.connection.execute("COMMIT")
            except BaseException:
                self.connection.execute("ROLLBACK")
                raise

    def _key(self, path):
        return str(Path(path).relative_to(self.racine))

    def _lire_json(self, path):
        row = self.connection.execute("SELECT value FROM documents WHERE key=?", (self._key(path),)).fetchone()
        return json.loads(row[0]) if row else None

    def _ecrire_json(self, path, value):
        self.connection.execute("INSERT OR REPLACE INTO documents VALUES (?, ?)",
                                (self._key(path), json.dumps(value, ensure_ascii=False, allow_nan=False)))

    def _modifier_json(self, path, transformation, defaut):
        with self.transaction_theme("pilot"):
            result = transformation(self._lire_json(path) or dict(defaut))
            self._ecrire_json(path, result)
            return result

    def maitrise_existe(self, theme):
        return self._lire_json(self._dossier_theme(theme) / "maitrise.json") is not None
