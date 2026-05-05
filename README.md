# pipewatch

> Lightweight observability agent for monitoring ETL pipeline health and alerting on anomalies.

---

## Installation

```bash
pip install pipewatch
```

Or install from source:

```bash
git clone https://github.com/yourorg/pipewatch.git && cd pipewatch && pip install -e .
```

---

## Usage

```python
from pipewatch import PipelineMonitor

monitor = PipelineMonitor(pipeline_name="daily_sales_etl")

@monitor.watch
def run_pipeline():
    # your ETL logic here
    extract()
    transform()
    load()

run_pipeline()
```

Configure alerting thresholds in `pipewatch.yaml`:

```yaml
alerts:
  row_count_drop_pct: 20
  max_null_rate: 0.05
  runtime_threshold_seconds: 300
  notify:
    slack_webhook: "https://hooks.slack.com/..."
    email: "data-team@yourorg.com"
```

Run the agent from the CLI:

```bash
pipewatch run --config pipewatch.yaml --pipeline daily_sales_etl
```

---

## Features

- 📊 Tracks row counts, null rates, and schema drift across pipeline runs
- ⚡ Real-time anomaly detection with configurable thresholds
- 🔔 Alerting via Slack, email, or webhook
- 🗂️ Lightweight — no external dependencies beyond standard ML libraries

---

## License

This project is licensed under the [MIT License](LICENSE).