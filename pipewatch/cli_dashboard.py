"""CLI entry point for the PipeWatch live dashboard."""

from __future__ import annotations

import argparse
import time
import sys
from typing import Optional

from pipewatch.dashboard import render_dashboard
from pipewatch.health_aggregator import AggregatedHealth
from pipewatch.snapshot_manager import SnapshotManager


def _build_aggregated_from_manager(manager: SnapshotManager) -> AggregatedHealth:
    """Reconstruct AggregatedHealth from the latest snapshot per pipeline."""
    agg = AggregatedHealth()
    for pipeline_id in manager.pipeline_ids():
        snapshot = manager.latest(pipeline_id)
        if snapshot is not None:
            agg.reports[pipeline_id] = snapshot.report
    return agg


def run_once(
    manager: SnapshotManager,
    title: str = "PipeWatch Dashboard",
    colorize: bool = True,
    out=None,
) -> None:
    """Print a single dashboard render to *out* (defaults to stdout)."""
    if out is None:
        out = sys.stdout
    agg = _build_aggregated_from_manager(manager)
    print(render_dashboard(agg, title=title, colorize=colorize), file=out)


def run_loop(
    manager: SnapshotManager,
    interval: float = 5.0,
    title: str = "PipeWatch Dashboard",
    colorize: bool = True,
    iterations: Optional[int] = None,
) -> None:
    """Continuously refresh the dashboard every *interval* seconds."""
    count = 0
    try:
        while True:
            print("\033[2J\033[H", end="")  # clear terminal
            run_once(manager, title=title, colorize=colorize)
            count += 1
            if iterations is not None and count >= iterations:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-dashboard",
        description="Live terminal dashboard for PipeWatch.",
    )
    parser.add_argument(
        "--interval", type=float, default=5.0,
        help="Refresh interval in seconds (default: 5).",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI color output.",
    )
    parser.add_argument(
        "--title", type=str, default="PipeWatch Dashboard",
        help="Dashboard title.",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Render once and exit instead of looping.",
    )
    return parser


def main() -> None:  # pragma: no cover
    parser = build_arg_parser()
    args = parser.parse_args()
    manager = SnapshotManager()
    colorize = not args.no_color

    if args.once:
        run_once(manager, title=args.title, colorize=colorize)
    else:
        run_loop(manager, interval=args.interval,
                 title=args.title, colorize=colorize)


if __name__ == "__main__":  # pragma: no cover
    main()
