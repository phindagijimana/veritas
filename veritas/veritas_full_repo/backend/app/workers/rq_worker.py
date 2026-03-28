from __future__ import annotations

"""
RQ worker entrypoint. Run from the backend directory:

    python -m app.workers.rq_worker

Requires Redis (REDIS_URL) and the same env as the API. Processes the queue named RQ_QUEUE_NAME.
"""

from redis import Redis
from rq import Worker

from app.core.config import get_settings, validate_production_settings


def main() -> None:
    settings = get_settings()
    validate_production_settings(settings)
    conn = Redis.from_url(settings.redis_url)
    conn.ping()
    worker = Worker([settings.rq_queue_name], connection=conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
