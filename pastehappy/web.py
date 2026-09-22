from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .csv_parser import parse_csv


def create_app(*, store, worker, browser, root: Path | str) -> Flask:
    root = Path(root)
    dist = root / "dist"
    app = Flask(__name__, static_folder=None)

    @app.get("/api/queue")
    def list_queue():
        return jsonify(store.list())

    @app.get("/api/queue/<job_id>")
    def get_job(job_id: str):
        job = store.get(job_id)
        return jsonify(job) if job else (jsonify(error="Job not found"), 404)

    @app.post("/api/queue/import")
    def import_queue():
        body = request.get_json(silent=True) or {}
        rows = parse_csv(body["csv"]) if "csv" in body else body.get("rows")
        if not isinstance(rows, list):
            return jsonify(error="Provide csv or rows"), 400
        return jsonify(store.import_rows(rows)), 201

    @app.post("/api/queue/start")
    def start_queue():
        started = worker.start(request.get_json(silent=True) or {})
        return jsonify(worker.status()), 202 if started else 409

    @app.post("/api/queue/pause")
    def pause_queue():
        worker.pause()
        return jsonify(worker.status())

    @app.post("/api/queue/resume")
    def resume_queue():
        worker.resume()
        return jsonify(worker.status())

    @app.post("/api/queue/stop")
    def stop_queue():
        worker.stop()
        return jsonify(worker.status())

    @app.post("/api/queue/clear")
    def clear_queue():
        return jsonify(worker.clear_queue())

    @app.post("/api/queue/current/skip")
    def skip_current():
        job = worker.skip_current()
        return jsonify(worker.status()) if job else (jsonify(error="No current job to skip"), 409)

    @app.post("/api/queue/<job_id>/retry")
    def retry_job(job_id: str):
        job = store.retry(job_id)
        return jsonify(job) if job else (jsonify(error="Job not found"), 404)

    @app.post("/api/queue/<job_id>/skip")
    def skip_job(job_id: str):
        job = store.skip(job_id)
        return jsonify(job) if job else (jsonify(error="Job not found"), 404)

    @app.get("/api/status")
    def get_status():
        return jsonify(**worker.status(), browser={
            "profileExists": browser.exists(), "open": browser.is_open, "headless": browser.headless,
        })

    @app.post("/api/browser/login")
    def browser_login():
        body = request.get_json(silent=True) or {}
        return jsonify(browser.call(browser.login(body.get("headless")), timeout=90)), 202

    @app.get("/")
    @app.get("/<path:path>")
    def static_app(path: str = ""):
        requested = dist / path
        if path and requested.is_file():
            return send_from_directory(dist, path)
        return send_from_directory(dist, "index.html")

    @app.errorhandler(Exception)
    def handle_error(error):
        app.logger.exception("Request failed")
        return jsonify(error=str(error)), 400

    return app
