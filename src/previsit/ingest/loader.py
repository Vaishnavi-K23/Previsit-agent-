"""Loads parsed FHIR rows into SQL Server. Bulk inserts only - 1175 patients
means ~1.26M rows across the 8 tables, so no row-by-row INSERTs.

Uses SQLAlchemy's `fast_executemany` engine option rather than calling
pyodbc's `cursor.fast_executemany` directly: raw pyodbc has a documented
gotcha where it infers each column's buffer size from the first row in a
batch, which can silently truncate later, longer values in the same
column (e.g. `display` text) when row lengths vary a lot, as ours do.
SQLAlchemy's mssql+pyodbc dialect handles this correctly.

Idempotency strategy: full wipe-and-reload, not merge/upsert. Simpler,
and the acceptance bar (SPEC.md Phase 2) is just "loading twice produces
identical row counts" - a full refresh trivially satisfies that. Fact
tables have no incoming foreign keys, so they TRUNCATE; dim_patient is
FK-referenced by all of them, and SQL Server disallows TRUNCATE on a
table any FK references (regardless of whether the referencing tables
currently hold rows) - so it gets DELETE instead (1175 rows, so the
usual DELETE-vs-TRUNCATE performance gap doesn't matter here).
"""

import re
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from previsit.config import settings
from previsit.ingest.fhir_parser import ParsedBundle, parse_bundle

SQL_DIR = Path(__file__).resolve().parents[3] / "sql"

# (dict key in the parsed row, target SQL column name) - listed separately
# because `class` is a Python keyword, so EncounterRow uses `class_`.
TABLE_SPECS: dict[str, list[tuple[str, str]]] = {
    "dim_patient": [
        ("patient_id", "patient_id"),
        ("source_resource_id", "source_resource_id"),
        ("birth_date", "birth_date"),
        ("gender", "gender"),
        ("deceased_flag", "deceased_flag"),
        ("city", "city"),
        ("state", "state"),
        ("postal_code", "postal_code"),
    ],
    "fact_encounter": [
        ("patient_id", "patient_id"),
        ("source_resource_id", "source_resource_id"),
        ("class_", "class"),
        ("type_code", "type_code"),
        ("type_display", "type_display"),
        ("start_datetime", "start_datetime"),
        ("end_datetime", "end_datetime"),
    ],
    "fact_observation": [
        ("patient_id", "patient_id"),
        ("encounter_id", "encounter_id"),
        ("source_resource_id", "source_resource_id"),
        ("code_system", "code_system"),
        ("code", "code"),
        ("display", "display"),
        ("value_numeric", "value_numeric"),
        ("value_string", "value_string"),
        ("unit", "unit"),
        ("effective_datetime", "effective_datetime"),
    ],
    "fact_condition": [
        ("patient_id", "patient_id"),
        ("source_resource_id", "source_resource_id"),
        ("code_system", "code_system"),
        ("code", "code"),
        ("display", "display"),
        ("onset_date", "onset_date"),
        ("abatement_date", "abatement_date"),
        ("clinical_status", "clinical_status"),
        ("verification_status", "verification_status"),
    ],
    "fact_medication": [
        ("patient_id", "patient_id"),
        ("source_resource_id", "source_resource_id"),
        ("code_system", "code_system"),
        ("code", "code"),
        ("display", "display"),
        ("status", "status"),
        ("authored_on", "authored_on"),
    ],
    "fact_procedure": [
        ("patient_id", "patient_id"),
        ("source_resource_id", "source_resource_id"),
        ("code_system", "code_system"),
        ("code", "code"),
        ("display", "display"),
        ("performed_datetime", "performed_datetime"),
    ],
    "fact_diagnostic_report": [
        ("patient_id", "patient_id"),
        ("source_resource_id", "source_resource_id"),
        ("code_system", "code_system"),
        ("code", "code"),
        ("display", "display"),
        ("effective_datetime", "effective_datetime"),
        ("conclusion_text", "conclusion_text"),
    ],
    "fact_immunization": [
        ("patient_id", "patient_id"),
        ("source_resource_id", "source_resource_id"),
        ("code_system", "code_system"),
        ("code", "code"),
        ("display", "display"),
        ("occurrence_datetime", "occurrence_datetime"),
    ],
}

# Load order matters: fact_observation.encounter_id has a FOREIGN KEY onto
# fact_encounter.source_resource_id, so encounters must land first.
LOAD_ORDER = [
    "dim_patient",
    "fact_encounter",
    "fact_observation",
    "fact_condition",
    "fact_medication",
    "fact_procedure",
    "fact_diagnostic_report",
    "fact_immunization",
]

# Reverse of LOAD_ORDER's dependency direction: wipe children before parents.
RESET_ORDER = list(reversed(LOAD_ORDER))

BUNDLE_KEY_BY_TABLE = {
    "dim_patient": "patients",
    "fact_condition": "conditions",
    "fact_encounter": "encounters",
    "fact_observation": "observations",
    "fact_medication": "medications",
    "fact_procedure": "procedures",
    "fact_diagnostic_report": "diagnostic_reports",
    "fact_immunization": "immunizations",
}


def get_engine() -> Engine:
    return create_engine(settings.mssql_connection_string, fast_executemany=True)


def ensure_database() -> None:
    """Creates the `previsit` database if it doesn't exist yet.

    Has to happen over a separate connection to `master`: you can't CREATE
    DATABASE from within a connection that's already scoped to the
    (possibly not-yet-existing) target database.
    """
    import pyodbc

    conn_str = (
        f"DRIVER={{{settings.mssql_driver}}};"
        f"SERVER={settings.mssql_host},{settings.mssql_port};"
        f"DATABASE=master;"
        f"UID=sa;PWD={settings.mssql_sa_password};"
        f"TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str, autocommit=True, timeout=10)
    try:
        conn.cursor().execute(
            f"IF DB_ID('{settings.mssql_database}') IS NULL "
            f"CREATE DATABASE [{settings.mssql_database}]"
        )
    finally:
        conn.close()


def _split_sql_batches(sql_text: str) -> list[str]:
    """Splits a .sql file on GO separators (SQLCMD batch syntax, not valid T-SQL)."""
    batches = re.split(r"^\s*GO\s*$", sql_text, flags=re.IGNORECASE | re.MULTILINE)
    return [b.strip() for b in batches if b.strip()]


def apply_schema(engine: Engine) -> None:
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for filename in ("01_schema.sql", "02_indexes.sql"):
            sql_text = (SQL_DIR / filename).read_text(encoding="utf-8")
            for batch in _split_sql_batches(sql_text):
                conn.execute(text(batch))


# SQL Server disallows TRUNCATE on any table referenced by a FOREIGN KEY,
# regardless of whether the referencing table currently holds rows -
# dim_patient (referenced by every fact table) and fact_encounter
# (referenced by fact_observation.encounter_id) both need DELETE instead.
TABLES_REQUIRING_DELETE = {"dim_patient", "fact_encounter"}


def reset_tables(engine: Engine) -> None:
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for table in RESET_ORDER:
            if table in TABLES_REQUIRING_DELETE:
                conn.execute(text(f"DELETE FROM {table}"))
            else:
                conn.execute(text(f"TRUNCATE TABLE {table}"))


def _bulk_insert(engine: Engine, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    spec = TABLE_SPECS[table]
    dict_keys = [k for k, _ in spec]
    sql_cols = [c for _, c in spec]
    stmt = text(
        f"INSERT INTO {table} ({', '.join(sql_cols)}) "
        f"VALUES ({', '.join(':' + k for k in dict_keys)})"
    )
    with engine.begin() as conn:
        conn.execute(stmt, [{k: row[k] for k in dict_keys} for row in rows])


def _iter_patient_bundles(fhir_dir: Path):
    non_patient_prefixes = ("hospitalInformation", "practitionerInformation")
    for path in sorted(fhir_dir.glob("*.json")):
        if path.name.startswith(non_patient_prefixes):
            continue
        yield path


def load_all(engine: Engine, fhir_dir: Path | None = None) -> dict[str, int]:
    fhir_dir = fhir_dir or (Path(settings.synthea_output_dir) / "fhir")

    accumulated: ParsedBundle = {key: [] for key in BUNDLE_KEY_BY_TABLE.values()}  # type: ignore[assignment]
    for path in _iter_patient_bundles(fhir_dir):
        import json

        bundle = json.loads(path.read_text(encoding="utf-8"))
        parsed = parse_bundle(bundle)
        for key in accumulated:
            accumulated[key].extend(parsed[key])

    reset_tables(engine)

    counts: dict[str, int] = {}
    for table in LOAD_ORDER:
        rows = accumulated[BUNDLE_KEY_BY_TABLE[table]]
        _bulk_insert(engine, table, rows)
        counts[table] = len(rows)

    return counts


def main() -> None:
    ensure_database()
    engine = get_engine()
    apply_schema(engine)
    counts = load_all(engine)
    print("Row counts loaded:")
    for table, count in counts.items():
        print(f"  {table:30s} {count}")


if __name__ == "__main__":
    main()
