"""Notification dispatch for alerts (console, file, future: email/wechat)."""

from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import DATA_DIR


class Notifier:
    """Dispatch alerts through various channels."""

    def __init__(self):
        self.log_file = DATA_DIR / "alerts.log"

    def notify(self, alerts: list[dict], channels: list[str] = None):
        """Dispatch alerts to specified channels."""
        if channels is None:
            channels = ["console", "file"]

        for channel in channels:
            handler = getattr(self, f"_notify_{channel}", None)
            if handler:
                handler(alerts)

    def _notify_console(self, alerts: list[dict]):
        """Print alerts to console with formatting."""
        if not alerts:
            print("[OK] 未触发任何告警。")
            return

        severity_chars = {
            "info": "[i]",
            "warning": "[!]",
            "critical": "[!!!]",
        }

        print()
        print("=" * 60)
        print(" [WARNING] Alerts")
        print("=" * 60)

        for alert in alerts:
            icon = severity_chars.get(alert.get("severity", "info"), "[?]")
            severity = alert.get("severity", "info").upper()
            print(f"\n  {icon} [{severity}] {alert.get('alert_type', '')}")
            print(f"  {alert.get('message', '')}")
            if alert.get("fund_code"):
                print(f"  基金: {alert['fund_code']}")
            print(f"  时间: {alert.get('triggered_at', datetime.now().isoformat())}")

        print()
        print("=" * 60)
        print(f"  共 {len(alerts)} 条告警")
        print("=" * 60)

    def _notify_file(self, alerts: list[dict]):
        """Append alerts to log file."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                for alert in alerts:
                    f.write(f"[{alert.get('triggered_at', datetime.now().isoformat())}] "
                            f"[{alert.get('severity', 'info').upper()}] "
                            f"{alert.get('alert_type', '')}: "
                            f"{alert.get('message', '')}\n")
        except Exception as e:
            print(f"  [Warn] Failed to write to alert log: {e}")

    def get_recent_alerts(self, repo, portfolio_id: int = None,
                          limit: int = 20) -> list:
        """Retrieve recent alerts from the database."""
        if repo:
            return repo.get_alerts(portfolio_id=portfolio_id, limit=limit)
        return []
