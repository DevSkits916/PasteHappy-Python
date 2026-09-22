from __future__ import annotations

import atexit
import logging

from waitress import serve

from pastehappy.browser import BrowserManager
from pastehappy.config import Config
from pastehappy.queue_store import QueueStore
from pastehappy.web import create_app
from pastehappy.worker import QueueWorker

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

config = Config.from_environment()
store = QueueStore(config.data_path).init()
browser = BrowserManager(
    profile_path=config.profile_path,
    headless=config.headless,
    executable_path=config.executable_path,
)
worker = QueueWorker(
    store=store,
    browser=browser,
    default_job_delay=config.default_job_delay,
    max_jobs_per_run=config.max_jobs_per_run,
)
app = create_app(store=store, worker=worker, browser=browser, root=config.root)


def shutdown() -> None:
    try:
        browser.call(worker.shutdown(), timeout=15)
    except Exception:
        logging.getLogger("pastehappy").exception("Failed to shut down cleanly")
    finally:
        browser.stop_loop()


atexit.register(shutdown)

if __name__ == "__main__":
    logging.info("PasteHappy running at http://localhost:%s", config.port)
    serve(app, host="0.0.0.0", port=config.port, threads=8)
