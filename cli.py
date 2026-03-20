"""
cli.py  —  EDA Agent · Command Line Interface
──────────────────────────────────────────────
Usage:
    python cli.py --csv data.csv --key YOUR_COHERE_KEY
    python cli.py --csv data.csv --key YOUR_COHERE_KEY --prompt "focus on churn"
    python cli.py --csv data.csv --key YOUR_COHERE_KEY --out report.txt
"""

import argparse
import os
import sys
import textwrap
import pandas as pd
from datetime import datetime
from agent_core import run_pipeline

# ── Terminal colours (safe fallback if unsupported) ────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"

def c(text, color):
    return f"{color}{text}{RESET}"

def header(title):
    line = "─" * 60
    print(f"\n{c(line, DIM)}")
    print(f"{c(f'  {title}', BOLD + CYAN)}")
    print(f"{c(line, DIM)}\n")

def step(name, status):
    icons = {"running": c("⟳ ", YELLOW), "done": c("✓ ", GREEN), "fail": c("✗ ", RED)}
    label = {
        "profiler":     "Data Profiler",
        "statistician": "Statistical Analyst",
        "pattern":      "Pattern Detector",
        "anomaly":      "Anomaly Scout",
        "synthesizer":  "Report Synthesizer",
    }.get(name, name)
    icon = icons.get(status, "  ")
    end = "\r" if status == "running" else "\n"
    print(f"  {icon}{label:<28} [{status.upper()}]", end=end, flush=True)

def print_section(title, content, color=CYAN):
    print(f"\n{c('━━ ' + title + ' ━━', BOLD + color)}\n")
    for line in content.split("\n"):
        print(f"  {line}")

# ── Main ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="eda-agent",
        description="EDA Agent — Autonomous data analysis via Cohere",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python cli.py --csv sales.csv --key co-xxxx
          python cli.py --csv sales.csv --key co-xxxx --prompt "focus on revenue trends"
          python cli.py --csv sales.csv --key co-xxxx --out report.txt --quiet
        """)
    )
    parser.add_argument("--csv",    required=True,  help="Path to input CSV file")
    parser.add_argument("--key",    required=False, help="Cohere API key (or set COHERE_API_KEY env var)")
    parser.add_argument("--prompt", default="",     help="Optional analysis focus")
    parser.add_argument("--out",    default="",     help="Save report to file (optional)")
    parser.add_argument("--quiet",  action="store_true", help="Only print the final report")
    args = parser.parse_args()

    # Resolve API key
    api_key = args.key or os.getenv("COHERE_API_KEY", "")
    if not api_key:
        print(c("Error: Provide --key or set the COHERE_API_KEY environment variable.", RED))
        sys.exit(1)

    # Load CSV
    if not os.path.exists(args.csv):
        print(c(f"Error: File not found — {args.csv}", RED))
        sys.exit(1)

    try:
        df = pd.read_csv(args.csv)
    except Exception as e:
        print(c(f"Error reading CSV: {e}", RED))
        sys.exit(1)

    if not args.quiet:
        header("EDA AGENT  ·  Powered by Cohere command-r")
        print(f"  {c('File:', DIM)}    {args.csv}")
        print(f"  {c('Shape:', DIM)}   {df.shape[0]:,} rows × {df.shape[1]} columns")
        print(f"  {c('Focus:', DIM)}   {args.prompt or 'General EDA'}")
        print(f"\n  {c('Running pipeline...', DIM)}\n")

    results = {}

    def on_step(name, status, result):
        if not args.quiet:
            step(name, status)
        if result:
            results[name] = result

    try:
        all_results = run_pipeline(api_key, df, args.prompt, on_step=on_step)
    except Exception as e:
        print(c(f"\nPipeline error: {e}", RED))
        sys.exit(1)

    if not args.quiet:
        print_section("DATA PROFILER",       all_results.get("profiler", ""),      CYAN)
        print_section("STATISTICAL ANALYSIS", all_results.get("statistician", ""), CYAN)
        print_section("PATTERN DETECTION",   all_results.get("pattern", ""),       CYAN)
        print_section("ANOMALY DETECTION",   all_results.get("anomaly", ""),       CYAN)

    # Always print final report
    print_section("FINAL EDA REPORT", all_results.get("synthesizer", ""), color="\033[95m")

    # Save to file
    out_path = args.out
    if not out_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = f"eda_report_{ts}.txt"

    report_text = "\n\n".join([
        f"EDA REPORT — {args.csv}",
        f"Generated: {datetime.now().isoformat()}",
        f"Focus: {args.prompt or 'General EDA'}",
        "=" * 60,
        f"DATA PROFILE\n{all_results.get('profiler','')}",
        f"STATISTICAL ANALYSIS\n{all_results.get('statistician','')}",
        f"PATTERN DETECTION\n{all_results.get('pattern','')}",
        f"ANOMALY DETECTION\n{all_results.get('anomaly','')}",
        f"FINAL REPORT\n{all_results.get('synthesizer','')}",
    ])

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    if not args.quiet:
        print(f"\n  {c('Report saved →', GREEN)} {out_path}\n")


if __name__ == "__main__":
    main()
