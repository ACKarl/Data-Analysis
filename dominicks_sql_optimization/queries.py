"""SQL queries used by benchmark.py.

The baseline queries work directly from raw tables.
The optimized queries use materialized summary tables created by build_optimization.py.
"""

BASELINE_QUERIES = {
    "Q1_weekly_movement": r"""
        WITH raw AS (
            SELECT 'Bottled Juice' AS category, week, move
            FROM wbjc_raw
            WHERE ok = 1
            UNION ALL
            SELECT 'Frozen Juice' AS category, week, move
            FROM wfrj_raw
            WHERE ok = 1
        )
        SELECT
            category,
            week,
            SUM(COALESCE(move, 0.0)) AS total_move
        FROM raw
        GROUP BY category, week
        ORDER BY category, week;
    """,

    "Q2_top_upc": r"""
        WITH upc_totals AS (
            SELECT
                'Bottled Juice' AS category,
                upc,
                SUM(COALESCE(move, 0.0)) AS total_move
            FROM wbjc_raw
            WHERE ok = 1
            GROUP BY upc

            UNION ALL

            SELECT
                'Frozen Juice' AS category,
                upc,
                SUM(COALESCE(move, 0.0)) AS total_move
            FROM wfrj_raw
            WHERE ok = 1
            GROUP BY upc
        ),
        ranked AS (
            SELECT
                category,
                upc,
                total_move,
                ROW_NUMBER() OVER (
                    PARTITION BY category
                    ORDER BY total_move DESC, upc ASC
                ) AS rn
            FROM upc_totals
        )
        SELECT category, upc, total_move
        FROM ranked
        WHERE rn = 1
        ORDER BY category;
    """,

    "Q3_price_tier": r"""
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
            AVG(profit) AS avg_profit
        FROM tiered
        WHERE price_tier IS NOT NULL
        GROUP BY category, price_tier
        ORDER BY
            category,
            CASE price_tier
                WHEN 'low' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'high' THEN 3
                WHEN 'premium' THEN 4
                ELSE 99
            END;
    """,
}

OPTIMIZED_QUERIES = {
    "Q1_weekly_movement": r"""
        SELECT
            category,
            week,
            SUM(total_move) AS total_move
        FROM juice_weekly_summary
        GROUP BY category, week
        ORDER BY category, week;
    """,

    "Q2_top_upc": r"""
        WITH upc_totals AS (
            SELECT
                category,
                upc,
                SUM(total_move) AS total_move
            FROM juice_weekly_summary
            GROUP BY category, upc
        ),
        ranked AS (
            SELECT
                category,
                upc,
                total_move,
                ROW_NUMBER() OVER (
                    PARTITION BY category
                    ORDER BY total_move DESC, upc ASC
                ) AS rn
            FROM upc_totals
        )
        SELECT category, upc, total_move
        FROM ranked
        WHERE rn = 1
        ORDER BY category;
    """,

    "Q3_price_tier": r"""
        SELECT
            category,
            price_tier,
            total_move,
            CASE
                WHEN profit_count = 0 THEN NULL
                ELSE profit_sum * 1.0 / profit_count
            END AS avg_profit
        FROM juice_price_tier_summary
        ORDER BY
            category,
            CASE price_tier
                WHEN 'low' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'high' THEN 3
                WHEN 'premium' THEN 4
                ELSE 99
            END;
    """,
}
