# Dominick's SQL Optimization Benchmark Result

- Repeats per version: **7** (after warm-up)
- Baseline/optimized outputs all match: **True**
- SQLite database: `dominicks.sqlite`

| Query | Baseline median (s) | Optimized median (s) | Latency reduction | Speedup | Correct |
|---|---:|---:|---:|---:|:---:|
| Q1_weekly_movement | 11.1487 | 0.0626 | 99.44% | 177.99× | True |
| Q2_top_upc | 4.2340 | 0.0426 | 98.99% | 99.30× | True |
| Q3_price_tier | 8.1219 | 0.0003 | 100.00% | 28309.04× | True |

## Overall 3-query workload
- Baseline median-sum: **23.5046 s**
- Optimized median-sum: **0.1056 s**
- Overall latency reduction: **99.55%**
- Overall speedup: **222.66×**
- Time saved per 3-query workload: **23.3990 s**

## Materialization / row reduction
- Optimization build time: **17.168 s**
- Valid raw rows (OK=1): **9,221,274**
- Weekly summary rows: **132,252**
- Valid-row count reduced at weekly analytical layer by: **98.57%**
- Approx. break-even: **0.73 complete 3-query workloads**

## Formula
`Latency reduction % = (baseline median - optimized median) / baseline median × 100`

`Speedup × = baseline median / optimized median`

## Resume wording
> Built a pre-aggregated `UPC × Week` analytical layer for Dominick's retail sales data and reduced the median-summed latency of three repeated analytical queries by **99.6%** (222.66× speedup), verified against equivalent raw-table SQL.
