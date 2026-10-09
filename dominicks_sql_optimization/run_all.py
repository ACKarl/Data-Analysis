#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd):
    print("\n>>> " + " ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description="Run the full Dominick's SQL optimization experiment.")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--db", default="dominicks.sqlite")
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--skip-import", action="store_true", help="Reuse an existing database")
    args = parser.parse_args()

    py = sys.executable
    here = Path(__file__).resolve().parent

    if not args.skip_import:
        run([py, str(here / "import_data.py"), "--data-dir", args.data_dir, "--db", args.db])

    run([py, str(here / "build_optimization.py"), "--db", args.db, "--results-dir", str(here / "results")])
    run([py, str(here / "benchmark.py"), "--db", args.db, "--repeats", str(args.repeats), "--results-dir", str(here / "results")])

    print("\nDONE. Open results/BENCHMARK_REPORT.md for the measured improvement.")


if __name__ == "__main__":
    main()
