import os

import uvicorn

from app.api import app


def _env_bool(name, default="false"):
    value = os.getenv(name, default)
    return value.lower() in {"1", "true", "yes", "on"}


def run():
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload_mode = _env_bool("API_RELOAD", "false")
    uvicorn.run("app.api:app", host=host, port=port, reload=reload_mode)


if __name__ == "__main__":
    run()
