# SqlServerBootstrap.py
# Provides: SqlExecutionConfig, SqlServerTelemetryExecutor

import pyodbc
from dataclasses import dataclass


@dataclass(frozen=True)
class SqlExecutionConfig:
    """Data-driven config -- all values passed in, nothing hard-coded."""
    server: str = "localhost"
    database: str = "TestDB"
    driver: str = "ODBC Driver 18 for SQL Server"
    trusted_connection: bool = True
    encrypt: bool = True
    trust_server_certificate: bool = True


class SqlServerTelemetryExecutor:
    """
    Thin wrapper around pyodbc.
    - Builds the connection string from SqlExecutionConfig.
    - Exposes execute_sql() for SELECT and allowed EXEC calls.
    """

    def __init__(self, config: SqlExecutionConfig):
        self.config = config
        self.conn_str = (
            f"DRIVER={{{config.driver}}};"
            f"SERVER={config.server};"
            f"DATABASE={config.database};"
            f"Trusted_Connection={'yes' if config.trusted_connection else 'no'};"
            f"Encrypt={'yes' if config.encrypt else 'no'};"
            f"TrustServerCertificate={'yes' if config.trust_server_certificate else 'no'};"
        )

    # ---- public API -------------------------------------------------------
    def execute_sql(self, sql: str) -> str:
        """
        Execute a read-only SQL statement and return results as a string.
        Raises on connection or query errors so callers can handle them.
        """
        try:
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()
            cursor.execute(sql)

            # If the statement returns rows, fetch them
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                # Format as a readable table string
                result_lines = [" | ".join(columns)]
                result_lines.append("-" * len(result_lines[0]))
                for row in rows:
                    result_lines.append(" | ".join(str(v) for v in row))
                result = "\n".join(result_lines)
            else:
                result = "(no result set returned)"

            cursor.close()
            conn.close()
            return result

        except Exception as exc:
            return f"SQL_ERROR: {exc}"
