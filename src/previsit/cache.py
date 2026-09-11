"""Persistent pre-visit card cache, keyed by patient_id (sql/04_card_cache.sql).

Exists specifically for a public deployment where every visitor shares one
LLM provider's small daily request quota: a card is expensive to produce
(one live, rate-limited LLM call) and cheap to re-read, so once any visitor
generates a patient's card, it should never need to be regenerated just
because a different visitor, a different session, or a restarted process
asks for the same patient again. Same wipe-and-reinsert idiom as the Phase 2
loader (previsit.ingest.loader) rather than a MERGE/upsert - simpler, and
this table only ever holds one row per patient_id.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from previsit.models import PreVisitCard


def get_cached_card(engine: Engine, patient_id: str) -> PreVisitCard | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT card_json FROM card_cache WHERE patient_id = :pid"),
            {"pid": patient_id},
        ).fetchone()
    if row is None:
        return None
    return PreVisitCard.model_validate_json(row[0])


def save_card(engine: Engine, card: PreVisitCard) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM card_cache WHERE patient_id = :pid"), {"pid": card.patient_id})
        conn.execute(
            text(
                "INSERT INTO card_cache (patient_id, card_json, generated_at, model_used) "
                "VALUES (:pid, :card_json, :generated_at, :model_used)"
            ),
            {
                "pid": card.patient_id,
                "card_json": card.model_dump_json(),
                "generated_at": card.generated_at,
                "model_used": card.model_used,
            },
        )
