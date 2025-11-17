import logging
import json
from typing import Dict, Any, List
from datetime import datetime
import sys

# Configure structured JSON logging
class JSONFormatter(logging.Formatter):
    """Log formatter that outputs structured JSON."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging(level: str = 'INFO', use_json: bool = True):
    """Set up structured logging for the application."""
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


class MetricsCollector:
    """Collect metrics for observability."""

    def __init__(self):
        self.metrics: Dict[str, Any] = {
            'total_emails_processed': 0,
            'total_summaries_generated': 0,
            'total_actions_executed': 0,
            'avg_response_time_ms': 0.0,
            'success_count': 0,
            'error_count': 0,
            'pending_approval_count': 0,
        }
        self.logger = logging.getLogger(__name__)

    def record_email_processed(self) -> None:
        """Record an email being processed."""
        self.metrics['total_emails_processed'] += 1

    def record_summary_generated(self) -> None:
        """Record a summary being generated."""
        self.metrics['total_summaries_generated'] += 1

    def record_action_executed(self, status: str) -> None:
        """Record an action being executed."""
        self.metrics['total_actions_executed'] += 1
        if status == 'success':
            self.metrics['success_count'] += 1
        elif status == 'failed':
            self.metrics['error_count'] += 1
        elif status == 'pending_approval':
            self.metrics['pending_approval_count'] += 1

    def record_response_time(self, time_ms: float) -> None:
        """Record response time in milliseconds."""
        # Simple moving average
        total = self.metrics['avg_response_time_ms'] * (self.metrics['total_emails_processed'] - 1)
        self.metrics['avg_response_time_ms'] = (total + time_ms) / self.metrics['total_emails_processed']

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        return self.metrics

    def export_metrics(self) -> str:
        """Export metrics as JSON."""
        return json.dumps(self.metrics, indent=2)

    def reset(self) -> None:
        """Reset all metrics."""
        for key in self.metrics:
            if isinstance(self.metrics[key], (int, float)):
                self.metrics[key] = 0 if isinstance(self.metrics[key], int) else 0.0
        self.logger.info("Metrics reset")


class RequestTracer:
    """Simple request tracing for observability."""

    def __init__(self):
        self.traces: Dict[str, List[str]] = {}
        self.logger = logging.getLogger(__name__)

    def start_trace(self, trace_id: str) -> None:
        """Start a new trace."""
        self.traces[trace_id] = [f"[START] {datetime.utcnow().isoformat()}"]

    def add_span(self, trace_id: str, span_name: str, data: Dict[str, Any]) -> None:
        """Add a span to a trace."""
        if trace_id not in self.traces:
            self.start_trace(trace_id)
        span_entry = f"[{span_name}] {json.dumps(data)}"
        self.traces[trace_id].append(span_entry)
        self.logger.info(f"Trace {trace_id}: {span_name}")

    def end_trace(self, trace_id: str) -> List[str]:
        """End a trace and return the trace log."""
        if trace_id in self.traces:
            self.traces[trace_id].append(f"[END] {datetime.utcnow().isoformat()}")
            return self.traces[trace_id]
        return []

    def get_trace(self, trace_id: str) -> List[str]:
        """Retrieve a trace."""
        return self.traces.get(trace_id, [])

    def clear_traces(self) -> None:
        """Clear all traces."""
        self.traces.clear()


# Global instances
logger = None
metrics_collector = None
request_tracer = None


def initialize_observability(level: str = 'INFO', use_json: bool = True):
    """Initialize all observability components."""
    global logger, metrics_collector, request_tracer
    logger = setup_logging(level, use_json)
    metrics_collector = MetricsCollector()
    request_tracer = RequestTracer()
