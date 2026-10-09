#!/usr/bin/env python3
import argparse
import json
import sqlite3
import time
from pathlib import Path

BUILD_SQL = r"""
DROP TABLE IF EXISTS juice_weekly_summary;
DROP TABLE IF EXISTS juice_price_tier_summary;

CREATE TABLE juice_weekly_summary AS
SELECT
    'Bottled Juice' AS category,
    upc,
    week,
    SUM(COALESCE(move, 0.0)) AS total_move,
    SUM(COALESCE(qty, 0.0)) AS total_qty,
    SUM(COALESCE(profit, 0.0)) AS total_profit,
    AVG(price) AS avg_price
FROM wbjc_raw
WHERE ok = 1
GROUP BY upc, week

UNION ALL

SELECT
    'Frozen Juice' AS category,
    upc,
    week,
    SUM(COALESCE(move, 0.0)) AS total_move,
    SUM(COALESCE(qty, 0.0)) AS total_qty,
    SUM(COALESCE(profit, 0.0)) AS total_profit,
    AVG(price) AS avg_price
FROM wfrj_raw
WHERE ok = 1
GROUP BY upc, week;

CREATE INDEX idx_weekly_category_week
    ON juice_weekly_summary(category, week);

CREATE INDEX idx_weekly_category_upc
    ON juice_weekly_summary(category, upc);

CREATE TABLE juice_price_tier_summary AS
WITH valid AS (
    SELECT 'Bottled Juice' AS category, price, profit, move
    FROM wbjc_raw
    WHERE ok = 1
      AND price IS NOT NULL
      AND profit IS NOT NULL
      AND move IS NOT NULL
      AND price > 0
      AND move > 0

    UNION ALL

    SELECT 'Frozen Juice' AS category, price, profit, move
    FROM wfrj_raw
    WHERE ok = 1
      AND price IS NOT NULL
      AND profit IS NOT NULL
      AND move IS NOT NULL
      AND price > 0
      AND move > 0
),
tiered AS (
    SELECT
        category,
        CASE
            WHEN price > 1.00 AND price <= 1.25 THEN 'low'
            WHEN price > 1.25 AND price <= 1.50 THEN 'medium'
            WHEN price > 1.50 AND price <= 2.00 THEN 'high'
            WHEN price > 2.00 THEN 'premium'
            ELSE NULL
        END AS price_tier,
        profit,
        move
    FROM valid
)
SELECT
    category,
    price_tier,
    SUM(move) AS total_move,
    SUM(profit) AS profit_sum,
    COUNT(profit) AS profit_count
FROM tiered
WHERE price_tier IS NOT NULL
GROUP BY category, price_tier;

CREATE UNIQUE INDEX idx_price_tier_category_tier
    ON juice_price_tier_summary(category, price_tier);
"""


def main():
    parser = argparse.ArgumentParser(description="Build materialized summary tables for Dominick's SQL optimization.")
    parser.add_argument("--db", default="dominicks.sqlite")
    parser.add_argument("--results-dir", default="results")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}. Run import_data.py first.")

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA cache_size=-262144;")

        raw_total = conn.execute(
            "SELECT (SELECT COUNT(*) FROM wbjc_raw) + (SELECT COUNT(*) FROM wfrj_raw);"
        ).fetchone()[0]
        valid_total = conn.execute(
            "SELECT (SELECT COUNT(*) FROM wbjc_raw WHERE ok=1) + (SELECT COUNT(*) FROM wfrj_raw WHERE ok=1);"
        ).fetchone()[0]

        start = time.perf_counter()
        conn.executescript(BUILD_SQL)
        conn.execute("ANALYZE;")
        conn.commit()
        build_seconds = time.perf_counter() - start

        weekly_rows = conn.execute("SELECT COUNT(*) FROM juice_weekly_summary;").fetchone()[0]
        price_rows = conn.execute("SELECT COUNT(*) FROM juice_price_tier_summary;").fetchone()[0]
    finally:
        conn.close()

    meta = {
        "build_seconds": build_seconds,
        "raw_rows": raw_total,
        "valid_rows_ok_1": valid_total,
        "weekly_summary_rows": weekly_rows,
        "price_tier_summary_rows": price_rows,
        "valid_to_weekly_row_reduction_pct": (
            (valid_total - weekly_rows) / valid_total * 100.0 if valid_total else None
        ),
        "valid_rows_per_weekly_summary_row": (
            valid_total / weekly_rows if weekly_rows else None
        ),
        "database_size_mib": db_path.stat().st_size / (1024 * 1024),
    }

    out = results_dir / "optimization_meta.json"
    out.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Optimization built in {build_seconds:.3f}s")
    print(f"Valid raw rows (OK=1): {valid_total:,}")
    print(f"Weekly summary rows:   {weekly_rows:,}")
    if valid_total:
        print(f"Row reduction:         {meta['valid_to_weekly_row_reduction_pct']:.2f}%")
    print(f"Metadata saved to: {out}")


if __name__ == "__main__":
    main()
