"""Build human-readable and structured reports from a MetricAggregator."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from pipewatch.metric_aggregator import MetricAggregator, MetricSummary


@dataclass
class AggregatorReport:
    """Structured report produced from a MetricAggregator snapshot."""

    summaries: List[MetricSummary] = field(default_factory=list)

    @property
    def total_pipelines(self) -> int:
        return len(self.summaries)

    @property
    def total_samples(self) -> int:
        return sum(s.samples for s in self.summaries)

    def highest_failure_rate(self) -> MetricSummary | None:
        """Return the summary with the highest mean failure rate, or None."""
        if not self.summaries:
            return None
        return max(self.summaries, key=lambda s: s.mean_failure_rate)

    def lowest_throughput(self) -> MetricSummary | None:
        """Return the summary with the lowest mean throughput, or None."""
        if not self.summaries:
            return None
        return min(self.summaries, key=lambda s: s.mean_throughput)

    def to_dict(self) -> dict:
        return {
            "total_pipelines": self.total_pipelines,
            "total_samples": self.total_samples,
            "summaries": [s.to_dict() for s in self.summaries],
        }

    def render_text(self) -> str:
        """Return a compact plain-text table suitable for CLI output."""
        if not self.summaries:
            return "No metric data available."

        header = (
            f"{'Pipeline':<30} {'Samples':>7} {'FailRate':>9} "
            f"{'Throughput':>11} {'Min TP':>8} {'Max TP':>8}"
        )
        separator = "-" * len(header)
        rows = [header, separator]
        for s in self.summaries:
            rows.append(
                f"{s.pipeline_id:<30} {s.samples:>7} "
                f"{s.mean_failure_rate:>9.4f} "
                f"{s.mean_throughput:>11.2f} "
                f"{s.min_throughput:>8.2f} "
                f"{s.max_throughput:>8.2f}"
            )
        rows.append(separator)
        rows.append(
            f"Totals — {self.total_pipelines} pipeline(s), "
            f"{self.total_samples} sample(s)"
        )
        return "\n".join(rows)


def build_report(aggregator: MetricAggregator) -> AggregatorReport:
    """Snapshot the current aggregator state into an AggregatorReport."""
    return AggregatorReport(summaries=aggregator.all_summaries())
