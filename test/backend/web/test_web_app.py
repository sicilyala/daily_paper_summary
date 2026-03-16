from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.web.app import create_app


class FakePaperSummaryService:
    def __init__(self, latest_newspaper: dict[str, str] | None = None):
        self.latest_newspaper = latest_newspaper
        self.jobs: dict[str, dict] = {}

    def create_job(self, *, delete_last_file: bool, config_path: str | None) -> dict:
        job = {
            "job_id": "job-001",
            "status": "queued",
            "delete_last_file": delete_last_file,
            "config_path": config_path,
            "result": None,
            "error": None,
        }
        self.jobs[job["job_id"]] = job
        return job

    def execute_job(self, job_id: str) -> None:
        job = self.jobs[job_id]
        job["status"] = "succeeded"
        job["result"] = {
            "generated": True,
            "summary_count": 3,
            "output_path": "newspaper/markdown/0311_papers.md",
            "skipped_reason": None,
            "emitted_ids": ["paper-1", "paper-2", "paper-3"],
        }

    def get_job(self, job_id: str) -> dict | None:
        return self.jobs.get(job_id)

    def get_latest_newspaper(self) -> dict[str, str] | None:
        return self.latest_newspaper


def _build_frontend_files(frontend_dir: Path) -> None:
    frontend_dir.mkdir(parents=True, exist_ok=True)
    (frontend_dir / "index.html").write_text(
        "<!doctype html><html><head><title>Daily Paper Summary</title></head><body>browser ui</body></html>",
        encoding="utf-8",
    )
    (frontend_dir / "styles.css").write_text("body { color: #111; }", encoding="utf-8")
    (frontend_dir / "app.js").write_text("console.log('ready');", encoding="utf-8")


def test_web_app_exposes_health_run_and_latest_newspaper(tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend"
    _build_frontend_files(frontend_dir)

    service = FakePaperSummaryService(
        latest_newspaper={
            "path": str(tmp_path / "newspaper" / "0311_papers.md"),
            "markdown": "# Daily Paper Summary\n\n## Paper 1\n\nBody",
            "html": "<h1>Daily Paper Summary</h1><h2>Paper 1</h2><p>Body</p>",
        }
    )
    client = TestClient(create_app(service=service, frontend_dir=frontend_dir))

    health_response = client.get("/api/health")
    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"

    create_response = client.post(
        "/api/runs",
        json={"delete_last_file": True, "config_path": "config/default_config.json"},
    )
    assert create_response.status_code == 202
    payload = create_response.json()
    assert payload["job_id"] == "job-001"
    assert payload["status"] in {"queued", "running", "succeeded"}

    job_response = client.get("/api/runs/job-001")
    assert job_response.status_code == 200
    assert job_response.json()["status"] == "succeeded"
    assert job_response.json()["result"]["summary_count"] == 3

    latest_response = client.get("/api/newspaper/latest")
    assert latest_response.status_code == 200
    assert latest_response.json()["path"].endswith("0311_papers.md")
    assert "<h1>Daily Paper Summary</h1>" in latest_response.json()["html"]


def test_web_app_serves_frontend_and_assets(tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend"
    _build_frontend_files(frontend_dir)

    client = TestClient(create_app(service=FakePaperSummaryService(), frontend_dir=frontend_dir))

    index_response = client.get("/")
    assert index_response.status_code == 200
    assert "Daily Paper Summary" in index_response.text

    asset_response = client.get("/assets/styles.css")
    assert asset_response.status_code == 200
    assert "color" in asset_response.text
