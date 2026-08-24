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
    import pyodbc

    conn_str = (
        f"DRIVER={{{settings.mssql_driver}}};"
        f"SERVER={settings.mssql_host},{settings.mssql_port};"
        f"DATABASE=master;"
        f"UID=sa;PWD={settings.mssql_sa_password};"
        f"TrustServerCertificate=yes;"
    )
    try:
        with pyodbc.connect(conn_str, timeout=5) as conn:
            row = conn.cursor().execute("SELECT @@VERSION").fetchone()
        version = row[0].splitlines()[0] if row else "unknown version"
        return True, version
    except Exception as exc:  # noqa: BLE001 - report exact driver/connection failure to the user
        return False, str(exc)


def check_qdrant() -> tuple[bool, str]:
    from qdrant_client import QdrantClient

    try:
        client = QdrantClient(
            host=settings.qdrant_host, port=settings.qdrant_http_port, timeout=5
        )
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
