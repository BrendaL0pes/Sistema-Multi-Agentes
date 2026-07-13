"""Run the requirements analysis pipeline from the command line."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from req_multiagent.orchestration.workflow import run_requirements_workflow


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Run the Requirements Engineering multi-agent pipeline."
    )
    parser.add_argument(
        "transcript",
        nargs="?",
        default="data/synthetic_transcripts/transcript_01_checkout.md",
        help="Path to a stakeholder transcript.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional Markdown file where the final report will be written.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="Optional SQLite database path for persisted workflow artifacts.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Run without saving results to SQLite.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute the CLI pipeline."""

    args = parse_args()
    result = run_requirements_workflow(
        transcript_path=PROJECT_ROOT / args.transcript,
        database_path=args.database,
        persist=not args.no_persist,
    )

    if not result.success:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.report_markdown, encoding="utf-8")
        print(f"Report written to {args.output.as_posix()}")
    else:
        print(result.report_markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
