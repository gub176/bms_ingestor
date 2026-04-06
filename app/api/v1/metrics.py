"""Monitoring endpoints for observability"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.services.batch_worker import MetricsCollector

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Global metrics collector (shared with batch worker)
_metrics_collector: MetricsCollector = None


def set_metrics_collector(collector: MetricsCollector):
    """Set global metrics collector"""
    global _metrics_collector
    _metrics_collector = collector


def format_metric_value(key: str, value) -> str:
    """Format metric value for display"""
    if key == "last_message_time":
        if value is None:
            return "N/A"
        try:
            # Value is asyncio event loop time (seconds since loop started)
            # Convert to relative time string
            ts = float(value)
            minutes = int(ts // 60)
            seconds = ts % 60
            if minutes > 0:
                return f"{minutes}m {seconds:.1f}s ago"
            else:
                return f"{seconds:.1f}s ago"
        except (ValueError, TypeError):
            return str(value)
    elif isinstance(value, float) and value == int(value):
        return str(int(value))
    elif isinstance(value, float):
        return f"{value:.2f}"
    else:
        return str(value)


METRICS_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="8">
    <title>BMS Cloud Platform - Monitoring</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        h1 { text-align: center; margin-bottom: 30px; color: #00d9ff; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .metric-card { background: #16213e; border-radius: 10px; padding: 20px; border-left: 4px solid #00d9ff; }
        .metric-card h3 { color: #888; font-size: 14px; margin-bottom: 10px; }
        .metric-value { font-size: 32px; font-weight: bold; color: #00d9ff; }
        .metric-card.error { border-left-color: #ff4757; background: #2d1b1e; }
        .metric-card.error h3 { color: #ff6b7a; }
        .metric-card.error .metric-value { color: #ff4757; }
        .section-title { grid-column: 1 / -1; font-size: 18px; color: #00d9ff; margin-top: 20px; border-bottom: 1px solid #333; padding-bottom: 10px; }
        .error-log { grid-column: 1 / -1; background: #2d1b1e; border-radius: 10px; padding: 20px; border: 1px solid #ff4757; max-height: 400px; overflow-y: auto; }
        .error-log h3 { color: #ff4757; margin-bottom: 15px; }
        .error-item { background: #1a1a2e; padding: 10px; margin-bottom: 10px; border-radius: 5px; border-left: 3px solid #ff4757; }
        .error-item .error-type { color: #ff6b7a; font-size: 12px; text-transform: uppercase; }
        .error-item .error-message { color: #eee; margin: 5px 0; font-family: monospace; font-size: 13px; }
        .error-item .error-time { color: #666; font-size: 11px; }
    </style>
</head>
<body>
    <h1>BMS Cloud Platform - Monitoring</h1>
    <div class="metrics-grid" id="metrics"></div>
    <p style="text-align:center;margin-top:20px;color:#666;">Auto-refresh: 8s</p>
    <script>
        const ERROR_KEYS = ['supabase_errors', 'json_errors', 'messages_dropped_total'];

        function is_error_key(key) {
            return ERROR_KEYS.includes(key) || key.toLowerCase().includes('error');
        }

        function formatErrorTime(isoString) {
            const date = new Date(isoString);
            return date.toLocaleString();
        }

        async function fetchMetrics() {
            const res = await fetch('/metrics/data');
            const data = await res.json();
            const stats = data.stats || {};
            const errors = data.errors || [];
            const entries = Object.entries(stats);

            // Separate error metrics from regular metrics
            const errorEntries = entries.filter(([k]) => is_error_key(k));
            const regularEntries = entries.filter(([k]) => !is_error_key(k));

            // Build HTML - metrics first, error log at bottom
            let html = '';

            // Error metrics section
            if (errorEntries.length > 0) {
                html += '<div class="section-title">⚠️ Error Counts</div>';
                html += errorEntries.map(([k, v]) => {
                    const isError = parseInt(v) > 0;
                    return '<div class="metric-card' + (isError ? ' error' : '') + '"><h3>' + k + '</h3><span class="metric-value">' + v + '</span></div>';
                }).join('');
            }

            // Regular metrics section
            html += '<div class="section-title">📊 Metrics</div>';
            html += regularEntries.map(([k, v]) => '<div class="metric-card"><h3>' + k + '</h3><span class="metric-value">' + v + '</span></div>').join('');

            // Error log section at bottom
            if (errors.length > 0) {
                html += '<div class="section-title">📋 Recent Errors</div>';
                html += '<div class="error-log">';
                html += '<h3>Last ' + errors.length + ' errors</h3>';
                // Show last 20 errors, newest first
                errors.slice(-20).reverse().forEach(function(err) {
                    html += '<div class="error-item">';
                    html += '<div class="error-type">' + err.type + '</div>';
                    html += '<div class="error-message">' + err.message.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>';
                    html += '<div class="error-time">' + formatErrorTime(err.timestamp) + '</div>';
                    html += '</div>';
                });
                html += '</div>';
            }

            document.getElementById('metrics').innerHTML = html;
        }
        fetchMetrics();
        setInterval(fetchMetrics, 8000);
    </script>
</body>
</html>
"""


@router.get("")
async def metrics_html():
    """Metrics dashboard (HTML)"""
    return HTMLResponse(content=METRICS_HTML)


@router.get("/data")
async def metrics_data():
    """Metrics data (JSON)"""
    if _metrics_collector:
        stats = await _metrics_collector.get_stats()
        errors = await _metrics_collector.get_recent_errors()
        # Format values for display
        return {
            "stats": {k: format_metric_value(k, v) for k, v in stats.items()},
            "errors": errors
        }
    return {"error": "Metrics collector not initialized"}


@router.get("/text")
async def metrics_text():
    """Metrics in Prometheus format"""
    if _metrics_collector:
        stats = await _metrics_collector.get_stats()
        lines = [f"{k} {v}" for k, v in stats.items() if isinstance(v, (int, float))]
        return HTMLResponse(content="\n".join(lines), media_type="text/plain")
    return {"error": "Metrics collector not initialized"}
