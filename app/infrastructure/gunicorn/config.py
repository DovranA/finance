import os

from app.core.config import get_settings

settings = get_settings()

forwarded_allow_ips = "*"
bind = f"{settings.app.host}:{settings.app.port}"

# Keep worker tuning configurable via env vars for Docker deployments.
workers = int(os.getenv("GUNICORN_WORKERS", "4"))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))

loglevel = os.getenv("GUNICORN_LOG_LEVEL", settings.app.log_level).lower()
accesslog = "-"
errorlog = "-"
capture_output = True
