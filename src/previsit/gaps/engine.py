"""Runs each sql/gaps/*.sql rule and returns typed Gap objects. No clinical
judgment happens in Python here - every rule is a plain parameterized SQL
query; this module just executes them and shapes the rows. By design, the
LLM never decides whether a screening is due - this is the deterministic core
that decision comes from.
"""

import argparse
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from previsit.gaps.definitions import RULES
from previsit.models import Gap

SQL_GAPS_DIR = Path(__file__).resolve().parents[3] / "sql" / "gaps"


def _run_rule(engine: Engine, sql_filename: str, patient_id: str | None, as_of: datetime) -> list[Gap]:
    sql_text = (SQL_GAPS_DIR / sql_filename).read_text(encoding="utf-8")
    with engine.connect() as conn:
        rows = conn.execute(text(sql_text), {"as_of": as_of, "patient_id": patient_id}).mappings().all()

    gaps = []
    for row in rows:
        raw_ids = row["source_resource_ids"] or ""
        ids = [s.strip() for s in raw_ids.split(",") if s.strip()]
        gaps.append(
            Gap(
                patient_id=row["patient_id"],
                gap_code=row["gap_code"],
                gap_title=row["gap_title"],
                severity=row["severity"],
                detail=row["detail"],
                source_resource_ids=ids,
                rule_version=row["rule_version"],
            )
        )
    return gaps


def check_care_gaps(
    engine: Engine, patient_id: str | None = None, as_of: datetime | None = None
) -> list[Gap]:
    """Runs every rule. `as_of` defaults to now - pass an explicit datetime for
    reproducible testing (e.g. boundary-condition tests need a fixed reference
    point, not "whenever the test happens to run")."""
    as_of = as_of or datetime.utcnow()
    all_gaps: list[Gap] = []
    for rule in RULES:
        all_gaps.extend(_run_rule(engine, rule.sql_filename, patient_id, as_of))
    return all_gaps


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic care-gap rules for one patient.")
    parser.add_argument("--patient", required=True, help="patient_id to check")
    args = parser.parse_args()

    from previsit.ingest.loader import get_engine

    engine = get_engine()
    gaps = check_care_gaps(engine, patient_id=args.patient)

    if not gaps:
        print(f"No care gaps found for patient {args.patient}.")
        return

    for gap in gaps:
        print(f"[{gap.severity.upper()}] {gap.gap_title} ({gap.gap_code}, {gap.rule_version})")
        print(f"    {gap.detail}")
        print(f"    sources: {', '.join(gap.source_resource_ids)}")


if __name__ == "__main__":
    main()
