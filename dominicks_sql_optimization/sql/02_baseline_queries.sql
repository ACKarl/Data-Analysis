-- BASELINE Q1: weekly movement rescans valid raw rows.
WITH raw AS (
    SELECT 'Bottled Juice' AS category, week, move FROM wbjc_raw WHERE ok = 1
    UNION ALL
    SELECT 'Frozen Juice' AS category, week, move FROM wfrj_raw WHERE ok = 1
)
SELECT category, week, SUM(COALESCE(move, 0.0)) AS total_move
FROM raw
GROUP BY category, week
ORDER BY category, week;

-- BASELINE Q2: top UPC rescans and re-aggregates raw rows.
WITH upc_totals AS (
    SELECT 'Bottled Juice' AS category, upc, SUM(COALESCE(move,0.0)) AS total_move
    FROM wbjc_raw WHERE ok=1 GROUP BY upc
    UNION ALL
    SELECT 'Frozen Juice' AS category, upc, SUM(COALESCE(move,0.0)) AS total_move
    FROM wfrj_raw WHERE ok=1 GROUP BY upc
), ranked AS (
    SELECT category, upc, total_move,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY total_move DESC, upc ASC) AS rn
    FROM upc_totals
)
SELECT category, upc, total_move
FROM ranked
WHERE rn=1
ORDER BY category;

-- BASELINE Q3: price-tier analysis recomputes CASE + GROUP BY from raw rows.
WITH valid AS (
    SELECT 'Bottled Juice' AS category, price, profit, move
    FROM wbjc_raw
    WHERE ok=1 AND price IS NOT NULL AND profit IS NOT NULL AND move IS NOT NULL AND price>0 AND move>0
    UNION ALL
    SELECT 'Frozen Juice' AS category, price, profit, move
    FROM wfrj_raw
    WHERE ok=1 AND price IS NOT NULL AND profit IS NOT NULL AND move IS NOT NULL AND price>0 AND move>0
), tiered AS (
    SELECT category,
           CASE
             WHEN price>1.00 AND price<=1.25 THEN 'low'
             WHEN price>1.25 AND price<=1.50 THEN 'medium'
             WHEN price>1.50 AND price<=2.00 THEN 'high'
             WHEN price>2.00 THEN 'premium'
             ELSE NULL
           END AS price_tier,
           profit, move
    FROM valid
)
SELECT category, price_tier, SUM(move) AS total_move, AVG(profit) AS avg_profit
FROM tiered
WHERE price_tier IS NOT NULL
GROUP BY category, price_tier
ORDER BY category,
         CASE price_tier WHEN 'low' THEN 1 WHEN 'medium' THEN 2 WHEN 'high' THEN 3 WHEN 'premium' THEN 4 ELSE 99 END;
