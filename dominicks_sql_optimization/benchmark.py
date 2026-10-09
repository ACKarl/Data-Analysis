#!/usr/bin/env python3
import argparse
import csv
import json
import math
import os
import sqlite3
import statistics
import time
from pathlib import Path

from queries import BASELINE_QUERIES, OPTIMIZED_QUERIES


def configure(conn):
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA cache_size=-262144;")


def timed_query(conn, sql):
    start = time.perf_counter()
    rows = conn.execute(sql).fetchall()
    elapsed = time.perf_counter() - start
    return elapsed, rows


def values_close(a, b, rel_tol=1e-8, abs_tol=1e-8):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=rel_tol, abs_tol=abs_tol)
    return a == b


def result_sets_match(a_rows, b_rows):
    if len(a_rows) != len(b_rows):
        return False, f"different row counts: {len(a_rows)} vs {len(b_rows)}"
    for i, (a, b) in enumerate(zip(a_rows, b_rows)):
        if len(a) != len(b):
            return False, f"row {i} has different column counts"
        for j, (x, y) in enumerate(zip(a, b)):
            if not values_close(x, y):
                return False, f"first mismatch at row {i}, col {j}: {x!r} vs {y!r}"
    return True, "match"


def percentile(values, p):
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)


def explain(conn, sql):
    return "\n".join(" | ".join(str(x) for x in row) for row in conn.execute("EXPLAIN QUERY PLAN " + sql).fetchall())


def main():
    parser = argparse.ArgumentParser(description="Benchmark baseline vs optimized Dominick's SQL queries.")
    parser.add_argument("--db", default="dominicks.sqlite")
    parser.add_argument("--repeats", type=int, default=7, help="Timed runs per version after warm-up")
    parser.add_argument("--results-dir", default="results")
    args = parser.parse_args()

    if args.repeats < 3:
        raise SystemExit("Use at least 3 repeats; 7 or 11 is recommended.")

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    results_dir = Path(args.results_dir)
    plans_dir = results_dir / "query_plans"
    results_dir.mkdir(parents=True, exist_ok=True)
    plans_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    configure(conn)

    records = []
    correctness_all = True

    try:
        for name in BASELINE_QUERIES:
            baseline_sql = BASELINE_QUERIES[name]
            optimized_sql = OPTIMIZED_QUERIES[name]

            # Correctness check and warm-up.
            _, baseline_rows = timed_query(conn, baseline_sql)
            _, optimized_rows = timed_query(conn, optimized_sql)
            match, match_note = result_sets_match(baseline_rows, optimized_rows)
            correctness_all = correctness_all and match

            baseline_times = []
            optimized_times = []

            # Alternate execution order to reduce systematic cache/order bias.
            for i in range(args.repeats):
                if i % 2 == 0:
                    t, _ = timed_query(conn, baseline_sql)
                    baseline_times.append(t)
                    t, _ = timed_query(conn, optimized_sql)
                    optimized_times.append(t)
                else:
                    t, _ = timed_query(conn, optimized_sql)
                    optimized_times.append(t)
                    t, _ = timed_query(conn, baseline_sql)
                    baseline_times.append(t)

            b_med = statistics.median(baseline_times)
            o_med = statistics.median(optimized_times)
            reduction = ((b_med - o_med) / b_med * 100.0) if b_med else None
            speedup = (b_med / o_med) if o_med else None

            rec = {
                "query": name,
                "correctness": match,
                "correctness_note": match_note,
                "result_rows": len(baseline_rows),
                "baseline_median_s": b_med,
                "optimized_median_s": o_med,
                "latency_reduction_pct": reduction,
                "speedup_x": speedup,
                "baseline_mean_s": statistics.mean(baseline_times),
                "optimized_mean_s": statistics.mean(optimized_times),
                "baseline_min_s": min(baseline_times),
                "optimized_min_s": min(optimized_times),
                "baseline_p95_s": percentile(baseline_times, 0.95),
                "optimized_p95_s": percentile(optimized_times, 0.95),
                "baseline_runs_s": baseline_times,
                "optimized_runs_s": optimized_times,
            }
            records.append(rec)

            (plans_dir / f"{name}_baseline.txt").write_text(explain(conn, baseline_sql), encoding="utf-8")
            (plans_dir / f"{name}_optimized.txt").write_text(explain(conn, optimized_sql), encoding="utf-8")

            print(
                f"{name}: baseline {b_med:.4f}s | optimized {o_med:.4f}s | "
                f"reduction {reduction:.2f}% | speedup {speedup:.2f}x | correct={match}"
            )

    finally:
        conn.close()

    baseline_suite = sum(r["baseline_median_s"] for r in records)
    optimized_suite = sum(r["optimized_median_s"] for r in records)
    suite_reduction = ((baseline_suite - optimized_suite) / baseline_suite * 100.0) if baseline_suite else None
    suite_speedup = (baseline_suite / optimized_suite) if optimized_suite else None
    suite_saving = baseline_suite - optimized_suite

    meta_path = results_dir / "optimization_meta.json"
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    build_seconds = meta.get("build_seconds")
    break_even = None
    if build_seconds is not None and suite_saving > 0:
        break_even = build_seconds / suite_saving

    summary = {
        "repeats": args.repeats,
        "all_results_match": correctness_all,
        "suite_baseline_median_sum_s": baseline_suite,
        "suite_optimized_median_sum_s": optimized_suite,
        "suite_latency_reduction_pct": suite_reduction,
        "suite_speedup_x": suite_speedup,
        "suite_time_saved_s": suite_saving,
        "optimization_build_seconds": build_seconds,
        "break_even_3_query_workloads": break_even,
        "queries": records,
    }

    # JSON with all timings.
    (results_dir / "benchmark_results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Flat CSV for easy review / portfolio evidence.
    csv_path = results_dir / "benchmark_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "query", "correctness", "result_rows",
            "baseline_median_s", "optimized_median_s",
            "latency_reduction_pct", "speedup_x",
            "baseline_mean_s", "optimized_mean_s",
            "baseline_min_s", "optimized_min_s",
            "baseline_p95_s", "optimized_p95_s",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow({k: r[k] for k in fields})

    # Human-readable report.
    report = []
    report.append("# Dominick's SQL Optimization Benchmark Result\n")
    report.append(f"- Repeats per version: **{args.repeats}** (after warm-up)")
    report.append(f"- Baseline/optimized outputs all match: **{correctness_all}**")
    report.append(f"- SQLite database: `{db_path}`\n")
    report.append("| Query | Baseline median (s) | Optimized median (s) | Latency reduction | Speedup | Correct |")
    report.append("|---|---:|---:|---:|---:|:---:|")
    for r in records:
        report.append(
            f"| {r['query']} | {r['baseline_median_s']:.4f} | {r['optimized_median_s']:.4f} | "
            f"{r['latency_reduction_pct']:.2f}% | {r['speedup_x']:.2f}× | {r['correctness']} |"
        )

    report.append("\n## Overall 3-query workload")
    report.append(f"- Baseline median-sum: **{baseline_suite:.4f} s**")
    report.append(f"- Optimized median-sum: **{optimized_suite:.4f} s**")
    report.append(f"- Overall latency reduction: **{suite_reduction:.2f}%**")
    report.append(f"- Overall speedup: **{suite_speedup:.2f}×**")
    report.append(f"- Time saved per 3-query workload: **{suite_saving:.4f} s**")

    if meta:
        report.append("\n## Materialization / row reduction")
        report.append(f"- Optimization build time: **{meta.get('build_seconds', float('nan')):.3f} s**")
        report.append(f"- Valid raw rows (OK=1): **{meta.get('valid_rows_ok_1', 0):,}**")
        report.append(f"- Weekly summary rows: **{meta.get('weekly_summary_rows', 0):,}**")
        rr = meta.get("valid_to_weekly_row_reduction_pct")
        if rr is not None:
            report.append(f"- Valid-row count reduced at weekly analytical layer by: **{rr:.2f}%**")
        if break_even is not None:
            report.append(f"- Approx. break-even: **{break_even:.2f} complete 3-query workloads**")

    report.append("\n## Formula")
    report.append("`Latency reduction % = (baseline median - optimized median) / baseline median × 100`")
    report.append("\n`Speedup × = baseline median / optimized median`")

    report.append("\n## Resume wording")
    if correctness_all:
        report.append(
            f"> Built a pre-aggregated `UPC × Week` analytical layer for Dominick's retail sales data and "
            f"reduced the median-summed latency of three repeated analytical queries by **{suite_reduction:.1f}%** "
            f"({suite_speedup:.2f}× speedup), verified against equivalent raw-table SQL."
        )
    else:
        report.append("> Do **not** use a performance claim yet: at least one optimized query did not match the baseline result.")

    report_path = results_dir / "BENCHMARK_REPORT.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    print("\nOverall workload:")
    print(f"  baseline median-sum: {baseline_suite:.4f}s")
    print(f"  optimized median-sum: {optimized_suite:.4f}s")
    print(f"  latency reduction: {suite_reduction:.2f}%")
    print(f"  speedup: {suite_speedup:.2f}x")
    if break_even is not None:
        print(f"  break-even: ~{break_even:.2f} complete 3-query workloads")
    print(f"\nReport: {report_path}")
    print(f"CSV:    {csv_path}")

    if not correctness_all:
        raise SystemExit("ERROR: correctness check failed. Do not use the performance numbers until fixed.")


if __name__ == "__main__":
    main()
