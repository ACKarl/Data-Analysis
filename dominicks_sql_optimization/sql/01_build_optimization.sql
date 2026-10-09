-- Dominick's SQL optimization layer.
-- Semantics aligned to the more complete juuuicy!.R workflow:
--   1) filter OK = 1
--   2) summarize by UPC x WEEK
--   3) use the same price-tier ranges used in the R analysis

DROP TABLE IF EXISTS juice_weekly_summary;
DROP TABLE IF EXISTS juice_price_tier_summary;

-- Optimization 1: filter and aggregate each raw category BEFORE UNION ALL.
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

-- Optimization 2: indexes match the project's repeated access paths.
CREATE INDEX idx_weekly_category_week
    ON juice_weekly_summary(category, week);
CREATE INDEX idx_weekly_category_upc
    ON juice_weekly_summary(category, upc);

-- Optimization 3: materialize the repeated price-tier aggregation.
CREATE TABLE juice_price_tier_summary AS
WITH valid AS (
    SELECT 'Bottled Juice' AS category, price, profit, move
    FROM wbjc_raw
    WHERE ok = 1
      AND price IS NOT NULL AND profit IS NOT NULL AND move IS NOT NULL
      AND price > 0 AND move > 0
    UNION ALL
    SELECT 'Frozen Juice' AS category, price, profit, move
    FROM wfrj_raw
    WHERE ok = 1
      AND price IS NOT NULL AND profit IS NOT NULL AND move IS NOT NULL
      AND price > 0 AND move > 0
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
