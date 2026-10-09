#!/usr/bin/env python3
import argparse
import csv
import os
import sqlite3
import sys
import time
from pathlib import Path

REQUIRED = ("UPC", "WEEK", "MOVE", "QTY", "PROFIT", "PRICE", "OK")


def to_float(v):
    if v is None:
        return None
    v = v.strip()
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def to_int(v):
    if v is None:
        return None
    v = v.strip()
    if v == "":
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def configure_for_import(conn: sqlite3.Connection):
    # Bulk-load settings. Safe enough for a reproducible local benchmark database.
    conn.execute("PRAGMA journal_mode=OFF;")
    conn.execute("PRAGMA synchronous=OFF;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA cache_size=-262144;")  # ~256 MiB if available
    conn.execute("PRAGMA locking_mode=EXCLUSIVE;")


def create_raw_table(conn: sqlite3.Connection, table: str):
    conn.execute(f"DROP TABLE IF EXISTS {table};")
    conn.execute(
        f"""
        CREATE TABLE {table} (
            upc    TEXT,
            week   INTEGER,
            move   REAL,
            qty    REAL,
            profit REAL,
            price  REAL,
            ok     INTEGER
        );
        """
    )


def import_csv(conn: sqlite3.Connection, csv_path: Path, table: str, batch_size: int = 50000):
    create_raw_table(conn, table)
    insert_sql = f"INSERT INTO {table} (upc, week, move, qty, profit, price, ok) VALUES (?, ?, ?, ?, ?, ?, ?);"

    start = time.perf_counter()
    rows = 0
    batch = []

    with csv_path.open("r", encoding="utf-8-sig", newline="", errors="replace") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise RuntimeError(f"No header found in {csv_path}")

        lookup = {name.upper(): name for name in reader.fieldnames}
        missing = [c for c in REQUIRED if c not in lookup]
        if missing:
            raise RuntimeError(
                f"{csv_path.name} is missing required columns: {missing}. "
                f"Available columns: {reader.fieldnames}"
            )

        conn.execute("BEGIN;")
        try:
            for row in reader:
                upc_raw = row.get(lookup["UPC"])
                upc = upc_raw.strip() if upc_raw is not None else None
                if upc == "":
                    upc = None

                batch.append(
                    (
                        upc,
                        to_int(row.get(lookup["WEEK"])),
                        to_float(row.get(lookup["MOVE"])),
                        to_float(row.get(lookup["QTY"])),
                        to_float(row.get(lookup["PROFIT"])),
                        to_float(row.get(lookup["PRICE"])),
                        to_int(row.get(lookup["OK"])),
                    )
                )
                rows += 1

                if len(batch) >= batch_size:
                    conn.executemany(insert_sql, batch)
                    batch.clear()
                    if rows % 500000 == 0:
                        elapsed = time.perf_counter() - start
                        print(f"  {table}: {rows:,} rows imported ({elapsed:.1f}s)")

            if batch:
                conn.executemany(insert_sql, batch)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    elapsed = time.perf_counter() - start
    print(f"Imported {rows:,} rows into {table} in {elapsed:.2f}s")
    return rows, elapsed


def main():
    parser = argparse.ArgumentParser(description="Import Dominick's juice CSVs into SQLite.")
    parser.add_argument("--data-dir", default="data", help="Folder containing wbjc.csv and wfrj.csv")
    parser.add_argument("--db", default="dominicks.sqlite", help="SQLite database path")
    parser.add_argument("--batch-size", type=int, default=50000)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    wbjc = data_dir / "wbjc.csv"
    wfrj = data_dir / "wfrj.csv"

    for p in (wbjc, wfrj):
        if not p.exists():
            print(f"ERROR: {p} not found.", file=sys.stderr)
            print("Extract the original RAR with 7-Zip/WinRAR and point --data-dir to that folder.", file=sys.stderr)
            sys.exit(2)

    db_path = Path(args.db)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        configure_for_import(conn)
        _, t1 = import_csv(conn, wbjc, "wbjc_raw", args.batch_size)
        _, t2 = import_csv(conn, wfrj, "wfrj_raw", args.batch_size)
        conn.execute("ANALYZE;")
        conn.commit()
    finally:
        conn.close()

    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"Database created: {db_path} ({size_mb:.1f} MiB)")
    print(f"Total import time: {t1 + t2:.2f}s")


if __name__ == "__main__":
    main()
