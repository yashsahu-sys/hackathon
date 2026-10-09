"""Load the raw CSVs into a DuckDB warehouse (one file, columnar, fast scans).

    python -m vani.data.warehouse      # builds data/private/warehouse.duckdb
"""
import logging
from pathlib import Path

import duckdb

from vani.config import get_settings

log = logging.getLogger(__name__)

TABLES = {
    "seller_profile": "gc_seller_profile.csv",
    "bot_calls": "gc_bot_calls.csv",
    "bot_call_turns": "gc_bot_call_turns.csv",
    "executive_calls": "gc_executive_calls.csv",
}
REQUIRED = {"seller_profile", "bot_calls"}


class WarehouseError(RuntimeError):
    pass


def build(raw_dir: Path, warehouse_path: Path) -> dict[str, int]:
    raw_dir, warehouse_path = Path(raw_dir), Path(warehouse_path)
    missing = [f for t, f in TABLES.items() if t in REQUIRED and not (raw_dir / f).exists()]
    if missing:
        raise WarehouseError(f"missing required files in {raw_dir}: {missing}")
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    con = duckdb.connect(str(warehouse_path))
    try:
        for table, filename in TABLES.items():
            path = raw_dir / filename
            if not path.exists():
                log.warning("optional file %s not found, creating empty %s", filename, table)
                continue
            con.execute(
                f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto(?, sample_size=-1, header=true)",
                [str(path)],
            )
            counts[table] = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        # Join keys as text everywhere, so lookups don't depend on CSV type inference.
        con.execute("CREATE OR REPLACE VIEW v_seller AS SELECT CAST(CAST(fk_glusr_usr_id AS BIGINT) AS VARCHAR) AS glid, * FROM seller_profile")
        con.execute("CREATE OR REPLACE VIEW v_bot_calls AS SELECT CAST(CAST(fk_glusr_usr_id AS BIGINT) AS VARCHAR) AS glid, CAST(attempt_id AS VARCHAR) AS attempt_key, * FROM bot_calls")
        if "bot_call_turns" in counts:
            con.execute("CREATE OR REPLACE VIEW v_turns AS SELECT CAST(attempt_id AS VARCHAR) AS attempt_key, * FROM bot_call_turns")
        else:
            con.execute("CREATE OR REPLACE TABLE bot_call_turns (attempt_id VARCHAR, fk_glusr_usr_id VARCHAR, turn_no INTEGER, speaker VARCHAR, start_sec DOUBLE, end_sec DOUBLE, text VARCHAR)")
            con.execute("CREATE OR REPLACE VIEW v_turns AS SELECT CAST(attempt_id AS VARCHAR) AS attempt_key, * FROM bot_call_turns")
    finally:
        con.close()
    return counts


if __name__ == "__main__":
    from vani.tools.console import utf8_console
    utf8_console()
    logging.basicConfig(level=logging.INFO)
    s = get_settings()
    print(build(s.resolve(s.raw_data_dir), s.resolve(s.warehouse_path)))
