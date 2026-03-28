from __future__ import annotations


from app.core.config import get_settings, validate_production_settings
from app.workers.job_worker import monitor_loop


if __name__ == "__main__":
    settings = get_settings()
    validate_production_settings(settings)
    monitor_loop(settings.job_monitor_interval_seconds)
