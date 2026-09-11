"""Loads parsed FHIR rows into SQL Server. Bulk inserts only - 1175 patients
means ~1.26M rows across the 8 tables, so no row-by-row INSERTs.

Uses pymssql, not pyodbc - see get_engine's own docstring for why: pyodbc
needs Microsoft's own ODBC Driver 18, a system package that can't be
installed on Streamlit Community Cloud through its supported customization
mechanism, confirmed directly in practice. Inserts are batched (see
_INSERT_BATCH_SIZE below) rather than sent as one bulk executemany() -
pushing ~975k rows (fact_observation, the largest table) as a single
network operation was observed dropping the connection mid-transfer over a
WAN link to a managed database.

Idempotency strategy: full wipe-and-reload, not merge/upsert. Simpler,
and the acceptance bar is just "loading twice produces identical row
counts" - a full refresh trivially satisfies that. Fact
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
from sqlalchemy.exc import DBAPIError

from previsit.config import settings
from previsit.ingest.fhir_parser import ParsedBundle, parse_bundle
from previsit.retry import with_retry

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
    """Uses pymssql, not pyodbc: pyodbc needs Microsoft's own ODBC Driver 18,
    a system-level package that requires adding Microsoft's private apt repo
    and accepting a EULA to install - which Streamlit Community Cloud's
    supported customization (`packages.txt`, plain Debian package names only)
    cannot do, confirmed directly in practice ("Can't open lib 'ODBC Driver
    18 for SQL Server' : file not found"). pymssql talks the same TDS wire
    protocol via FreeTDS, an ordinary open-source package with no EULA,
    which is installable that way - and works identically against local
    Docker SQL Server, Azure SQL Database, or any other SQL Server, since
    the wire protocol is the same regardless of which client library speaks
    it. Trade-off: pymssql's SQLAlchemy dialect doesn't support
    `fast_executemany` (a pyodbc-specific feature) - bulk inserts still
    batch efficiently through pymssql's own executemany, just not via that
    specific flag.

    Every caller of this function - not just this module's own load/reset
    functions, but agent/tools.py, guardrails.py, the Streamlit app, the
    FastAPI and MCP servers - gets the same protection, because a managed
    database can transiently refuse a brand-new connection at any time, not
    just during a bulk load: Azure SQL Database's free offer has returned
    error 40613 ("not currently available, retry later") on a plain ad-hoc
    query, well after the initial ingest had already finished successfully.
    A `connect_args={"timeout": ...}` engine has no way to recover from that
    - the failure happens before there's a live connection for anything to
    retry - so a custom `creator` is used instead: the *creation* of the raw
    connection itself goes through with_retry, protecting every query this
    engine will ever run, not just the ones this module happens to wrap.

    Separately, a serverless/free-tier database also auto-pauses after
    inactivity, and the first connection after a pause has to wait for it to
    resume (observed taking >5s, comfortably under the 45s timeout below) -
    a generous timeout costs nothing for an already-warm connection (local
    Docker SQL Server included), it only matters for a real cold start.
    """
    timeout = 45 if settings.mssql_is_managed else None

    def creator():
        import pymssql

        kwargs = {"login_timeout": timeout} if timeout else {}
        return with_retry(
            lambda: pymssql.connect(
                server=settings.mssql_host,
                port=str(settings.mssql_port),
                user=settings.mssql_username,
                password=settings.mssql_sa_password,
                database=settings.mssql_database,
                **kwargs,
            ),
            (pymssql.Error,),
        )

    return create_engine("mssql+pymssql://", creator=creator)


def ensure_database() -> None:
    """Creates the `previsit` database if it doesn't exist yet.

    Has to happen over a separate connection to `master`: you can't CREATE
    DATABASE from within a connection that's already scoped to the
    (possibly not-yet-existing) target database.

    Skipped entirely when settings.mssql_is_managed is True - a managed
    cloud database (e.g. Azure SQL Database's free offer) needs to be
    provisioned through the provider's own console, not this CREATE
    DATABASE statement, specifically so you land on the free tier you
    picked rather than whatever this statement would default to.
    """
    if settings.mssql_is_managed:
        return

    import pymssql

    conn = pymssql.connect(
        server=settings.mssql_host,
        port=str(settings.mssql_port),
        user=settings.mssql_username,
        password=settings.mssql_sa_password,
        database="master",
        autocommit=True,
        login_timeout=10,
    )
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


# A managed database (Azure SQL Database's free offer, seen directly in
# practice) can transiently refuse a new connection while it's resuming or
# rebalancing - error 40613, "Database is not currently available. Please
# retry the connection later." - Microsoft's own documented transient-fault
# code, expected to be retried, not treated as a real failure. A dropped
# mid-transfer connection surfaces the same DBAPIError family. See
# previsit.retry for why the backoff is shaped the way it is.
def _with_retry(fn):
    return with_retry(fn, (DBAPIError,))


def apply_schema(engine: Engine) -> None:
    for filename in ("01_schema.sql", "02_indexes.sql", "03_chief_complaint.sql", "04_card_cache.sql"):
        sql_text = (SQL_DIR / filename).read_text(encoding="utf-8")
        batches = _split_sql_batches(sql_text)

        def run_file(batches=batches):
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                for batch in batches:
                    conn.execute(text(batch))

        _with_retry(run_file)


# SQL Server disallows TRUNCATE on any table referenced by a FOREIGN KEY,
# regardless of whether the referencing table currently holds rows -
# dim_patient (referenced by every fact table) and fact_encounter
# (referenced by fact_observation.encounter_id) both need DELETE instead.
TABLES_REQUIRING_DELETE = {"dim_patient", "fact_encounter"}


def reset_tables(engine: Engine) -> None:
    def run():
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            # card_cache (sql/04_card_cache.sql) references dim_patient but isn't
            # part of LOAD_ORDER/RESET_ORDER at all - it's populated by actual
            # card generation later, not by this FHIR load. Still has to be
            # cleared before dim_patient below, or dim_patient's DELETE would hit
            # a foreign key violation from these leftover rows - and clearing it
            # here is correct anyway: a fresh Synthea regeneration means new
            # random patient_ids, so any previously-cached card is for a patient
            # that no longer exists after this reload.
            conn.execute(text("TRUNCATE TABLE card_cache"))
            for table in RESET_ORDER:
                if table in TABLES_REQUIRING_DELETE:
                    conn.execute(text(f"DELETE FROM {table}"))
                else:
                    conn.execute(text(f"TRUNCATE TABLE {table}"))

    _with_retry(run)


# fact_observation alone is ~975k rows for the full 1175-patient population -
# pushing that as a single executemany() worked fine against local Docker SQL
# Server, but over a WAN connection to a managed database it dropped the
# connection mid-transfer in practice ("communication link failure"). Batching
# keeps each network operation short enough not to trip whatever timeout or
# resource limit caused that; retrying per-batch (via _with_retry above), on a
# fresh connection each attempt, means a transient drop only costs the one
# in-flight batch, not the whole table, since every prior batch already
# committed on its own.
_INSERT_BATCH_SIZE = 5000


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
    payload = [{k: row[k] for k in dict_keys} for row in rows]

    for start in range(0, len(payload), _INSERT_BATCH_SIZE):
        batch = payload[start : start + _INSERT_BATCH_SIZE]

        def run_batch(batch=batch):
            with engine.begin() as conn:
                conn.execute(stmt, batch)

        _with_retry(run_batch)


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
