import unittest
import time
import threading
import sys
import os
from urllib import request

# Add scripts dir to path if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.observability import metrics, tracing, AlertManager

class TestObservability(unittest.TestCase):
    def setUp(self):
        # Use the global metrics instance
        self.metrics = metrics
        # Start server if not started (it handles check internally)
        # Note: port is 8000 by default in global instance.
        self.metrics.start_server()
        time.sleep(1)

    def test_metrics_endpoint(self):
        try:
            # Global instance uses port 8000
            req = request.Request("http://localhost:8000/metrics")
            with request.urlopen(req) as response:
                self.assertEqual(response.status, 200)
                content = response.read().decode('utf-8')
                self.assertIn("tasks_created_total", content)
        except Exception as e:
            self.fail(f"Metrics endpoint failed: {e}")

    def test_tracing(self):
        tracer = tracing.get_tracer()
        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test_attr", "value")

    def test_alerts(self):
        alert_file = "tests/test_alerts.log"
        if os.path.exists(alert_file):
            os.remove(alert_file)

        alerts = AlertManager(alert_file)
        alerts.send_alert("INFO", "Test alert")

        with open(alert_file, "r") as f:
            content = f.read()
            self.assertIn("Test alert", content)

        if os.path.exists(alert_file):
            os.remove(alert_file)

if __name__ == '__main__':
    unittest.main()
