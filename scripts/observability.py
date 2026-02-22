import logging
import os
import sys
import threading
import time
import json
from datetime import datetime
from urllib import request, error

# Prometheus
try:
    from prometheus_client import start_http_server, Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# OpenTelemetry
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
    from opentelemetry.sdk.resources import Resource
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

# Add scripts dir to path if running directly
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.config_loader import config
    from scripts.db_config import get_connection
except ImportError:
    from config_loader import config
    from db_config import get_connection

# Setup Logger
logger = logging.getLogger("observability")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class MetricsManager:
    """Manages Prometheus metrics."""

    def __init__(self, port=8000):
        self.port = port
        self.server_started = False

        if PROMETHEUS_AVAILABLE:
            # Counters
            self.tasks_created = Counter('tasks_created_total', 'Total number of tasks created')
            self.tasks_completed = Counter('tasks_completed_total', 'Total number of tasks completed')
            self.tasks_failed = Counter('tasks_failed_total', 'Total number of tasks failed')

            self.agents_spawned = Counter('agents_spawned_total', 'Total number of agents spawned', ['agent_type'])
            self.agents_failed = Counter('agents_failed_total', 'Total number of agents failed', ['agent_type'])

            # Histograms
            self.task_duration = Histogram('task_duration_seconds', 'Time taken to complete a task')
            self.agent_task_duration = Histogram('agent_task_duration_seconds', 'Time taken for agent subtask', ['agent_type'])

            # Gauges
            self.active_agents = Gauge('active_agents_count', 'Number of currently active agents')
        else:
            logger.warning("Prometheus client not installed. Metrics will be disabled.")

    def start_server(self):
        """Start Prometheus metrics server."""
        if PROMETHEUS_AVAILABLE and not self.server_started:
            try:
                start_http_server(self.port)
                self.server_started = True
                logger.info(f"Metrics server started on port {self.port}")
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")

class TracingManager:
    """Manages OpenTelemetry tracing."""

    def __init__(self, service_name="agent-swarm"):
        self.tracer = None
        if OPENTELEMETRY_AVAILABLE:
            resource = Resource(attributes={
                "service.name": service_name
            })

            provider = TracerProvider(resource=resource)

            # Use ConsoleSpanExporter for now (can act as a log of traces)
            # In production, use OTLPSpanExporter
            processor = SimpleSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)

            trace.set_tracer_provider(provider)
            self.tracer = trace.get_tracer(service_name)
        else:
            logger.warning("OpenTelemetry not installed. Tracing will be disabled.")

    def get_tracer(self):
        if self.tracer:
            return self.tracer

        # Return a dummy tracer that returns a nullcontext
        class DummyTracer:
            def start_as_current_span(self, name):
                import contextlib
                return contextlib.nullcontext()
        return DummyTracer()

class AlertManager:
    """Manages system alerts."""

    def __init__(self, alert_file="logs/alerts.log"):
        self.alert_file = alert_file

        # Ensure log dir exists
        log_dir = os.path.dirname(alert_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def send_alert(self, level: str, message: str, context: dict = None):
        """
        Send an alert.
        For now, this logs to a file. In production, this could send to Slack/PagerDuty.
        """
        timestamp = datetime.now().isoformat()
        alert = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "context": context or {}
        }

        # Log to file
        try:
            with open(self.alert_file, "a") as f:
                f.write(json.dumps(alert) + "\n")
        except Exception as e:
            logger.error(f"Failed to write alert to file: {e}")

        # Log to console if critical
        if level.upper() == "CRITICAL":
            logger.critical(f"ALERT: {message}")

class HealthCheck:
    """System health checks."""

    @staticmethod
    def check_db():
        """Check database connection."""
        try:
            conn = get_connection()
            conn.execute("SELECT 1")
            conn.close()
            return True, "Database connection successful"
        except Exception as e:
            return False, f"Database check failed: {e}"

    @staticmethod
    def check_openclaw():
        """Check OpenClaw gateway connectivity."""
        url = config.openclaw.gateway
        try:
            # Simple check to see if port is open / service responds
            # Since we don't know the exact health endpoint, we'll try the root
            req = request.Request(url, method='GET')
            with request.urlopen(req, timeout=2) as response:
                return True, f"OpenClaw gateway reachable ({response.status})"
        except error.URLError as e:
             # If it's a connection refused, it's definitely down.
             # If it's a 404, the service might be up but the endpoint is wrong.
             if hasattr(e, 'code'):
                 return True, f"OpenClaw gateway reachable (HTTP {e.code})"
             return False, f"OpenClaw check failed: {e}"
        except Exception as e:
            return False, f"OpenClaw check failed: {e}"

# Global instances
metrics = MetricsManager()
tracing = TracingManager()
alerts = AlertManager()
