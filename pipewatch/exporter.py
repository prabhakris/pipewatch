"""Export pipeline metrics and alerts to various output formats."""

from __future__ import annotations

import json
import csv
import io
from typing import List, Union

from pipewatch.metrics import PipelineMetric, to_dict as metric_to_dict
from pipewatch.alerts import Alert, to_dict as alert_to_dict
from pipewatch.pipeline_runner import RunReport


Exportable = Union[PipelineMetric, Alert, RunReport]


def to_json(items: List[Exportable], indent: int = 2) -> str:
    """Serialize a list of metrics, alerts, or run reports to a JSON string."""
    records = []
    for item in items:
        if isinstance(item, RunReport):
            records.append(item.to_dict())
        elif isinstance(item, Alert):
            records.append(alert_to_dict(item))
        elif isinstance(item, PipelineMetric):
            records.append(metric_to_dict(item))
        else:
            raise TypeError(f"Unsupported export type: {type(item)!r}")
    return json.dumps(records, indent=indent, default=str)


def to_csv(metrics: List[PipelineMetric]) -> str:
    """Serialize a list of PipelineMetric objects to a CSV string."""
    if not metrics:
        return ""

    fieldnames = list(metric_to_dict(metrics[0]).keys())
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for metric in metrics:
        writer.writerow(metric_to_dict(metric))
    return output.getvalue()


def to_jsonl(items: List[Exportable]) -> str:
    """Serialize items to newline-delimited JSON (one object per line)."""
    lines = []
    for item in items:
        if isinstance(item, RunReport):
            record = item.to_dict()
        elif isinstance(item, Alert):
            record = alert_to_dict(item)
        elif isinstance(item, PipelineMetric):
            record = metric_to_dict(item)
        else:
            raise TypeError(f"Unsupported export type: {type(item)!r}")
        lines.append(json.dumps(record, default=str))
    return "\n".join(lines)
