"""Tests de engine.timeutil et de la déduplication (P1-B1)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import engine.session.runner as runner_mod
import engine.srs.fsrs as fsrs_mod
from engine.timeutil import normaliser_utc


def test_naif_interprete_comme_utc():
    d = datetime(2026, 1, 5, 8, 0, 0)
    n = normaliser_utc(d)
    assert n.tzinfo == timezone.utc
    assert n.hour == 8


def test_converti_vers_utc():
    fuseau = timezone(timedelta(hours=2))
    d = datetime(2026, 1, 5, 10, 0, 0, tzinfo=fuseau)
    n = normaliser_utc(d)
    assert n.tzinfo == timezone.utc
    assert n.hour == 8  # 10h +02:00 == 08h UTC


def test_utc_inchange():
    d = datetime(2026, 1, 5, 8, 0, 0, tzinfo=timezone.utc)
    assert normaliser_utc(d) == d


def test_une_seule_definition_partagee():
    """fsrs et runner partagent la même fonction (source unique)."""
    assert fsrs_mod.normaliser_utc is normaliser_utc
    assert runner_mod._normaliser_utc is normaliser_utc
