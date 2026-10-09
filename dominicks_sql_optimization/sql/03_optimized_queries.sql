-- OPTIMIZED Q1: scan the UPC x WEEK analytical layer, not raw transactions.
SELECT category, week, SUM(total_move) AS total_move
FROM juice_weekly_summary
GROUP BY category, week
ORDER BY category, week;

-- OPTIMIZED Q2: aggregate the much smaller UPC x WEEK summary.
WITH upc_totals AS (
    SELECT category, upc, SUM(total_move) AS total_move
    FROM juice_weekly_summary
    GROUP BY category, upc
), ranked AS (
    SELECT category, upc, total_move,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY total_move DESC, upc ASC) AS rn
    FROM upc_totals
)
SELECT category, upc, total_move
FROM ranked
WHERE rn=1
ORDER BY category;

-- OPTIMIZED Q3: the price-tier aggregation has already been materialized.
SELECT category,
       price_tier,
       total_move,
       CASE WHEN profit_count=0 THEN NULL ELSE profit_sum * 1.0 / profit_count END AS avg_profit
FROM juice_price_tier_summary
ORDER BY category,
         CASE price_tier WHEN 'low' THEN 1 WHEN 'medium' THEN 2 WHEN 'high' THEN 3 WHEN 'premium' THEN 4 ELSE 99 END;
