"""Phase 0 acceptance check: confirm SQL Server and Qdrant are reachable
from Python. Run with: python -m previsit.healthcheck

Connects to SQL Server's default `master` database rather than the app
database — `previsit` doesn't exist until the Phase 2 schema is applied,
and this script only proves connectivity, not schema readiness.
"""

import sys

from previsit.config import settings

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def check_sqlserver() -> tuple[bool, str]:
    # pymssql, not pyodbc - see previsit.ingest.loader.get_engine for why:
    # pyodbc needs Microsoft's own ODBC Driver 18, which can't be installed
    # on Streamlit Community Cloud through its supported customization
    # mechanism, confirmed directly in practice.
    import pymssql

    # A managed/serverless database (e.g. Azure SQL Database's free offer)
    # auto-pauses after inactivity - the first connection after a pause has
    # to wait for it to resume, which a short timeout would misreport as a
    # real connection failure. See previsit.ingest.loader.get_engine.
    timeout = 45 if settings.mssql_is_managed else 5
    try:
        conn = pymssql.connect(
            server=settings.mssql_host,
            port=str(settings.mssql_port),
            user=settings.mssql_username,
            password=settings.mssql_sa_password,
            database="master",
            login_timeout=timeout,
        )
        try:
            cur = conn.cursor()
            cur.execute("SELECT @@VERSION")
            row = cur.fetchone()
        finally:
            conn.close()
        version = row[0].splitlines()[0] if row else "unknown version"
        return True, version
    except Exception as exc:  # noqa: BLE001 - report exact driver/connection failure to the user
        return False, str(exc)


def check_qdrant() -> tuple[bool, str]:
    from previsit.retrieval.vector_tools import get_client

    try:
        client = get_client(timeout=5)
        collections = client.get_collections()
        return True, f"{len(collections.collections)} collection(s) present"
    except Exception as exc:  # noqa: BLE001 - report exact connection failure to the user
        return False, str(exc)


def main() -> int:
    checks = {
        "SQL Server": check_sqlserver,
        "Qdrant": check_qdrant,
    }

    all_ok = True
    for name, check in checks.items():
        ok, detail = check()
        all_ok &= ok
        color = GREEN if ok else RED
        status = "OK" if ok else "FAIL"
        print(f"{color}[{status}]{RESET} {name}: {detail}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
