#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 run_all.py --data-dir "data" --repeats 7
printf '\nFinished. Open results/BENCHMARK_REPORT.md\n'
