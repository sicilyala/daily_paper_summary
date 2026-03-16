"""FastAPI application for browser-based execution and display."""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.config.web_config import WebAppConfig
from backend.web.service import PaperSummaryService


class RunRequest(BaseModel):
    """Payload for starting a new pipeline job."""

    delete_last_file: bool = False
    config_path: str | None = None


def create_app(
    *,
    service: PaperSummaryService | object | None = None,
    frontend_dir: Path | None = None,
) -> FastAPI:
    config = WebAppConfig()
    resolved_frontend_dir = frontend_dir or config.frontend_dir
    app = FastAPI(title="Daily Paper Summary Web", version="0.1.0")
    app.state.paper_summary_service = service or PaperSummaryService(markdown_dir=config.markdown_dir)

    app.mount("/assets", StaticFiles(directory=str(resolved_frontend_dir)), name="assets")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(resolved_frontend_dir / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": "daily-paper-summary-web"}

    @app.post("/api/runs", status_code=202)
    async def create_run(request: RunRequest) -> dict:
        active_service = app.state.paper_summary_service
        job = active_service.create_job(
            delete_last_file=request.delete_last_file,
            config_path=request.config_path,
        )
        if hasattr(active_service, "start_job"):
            active_service.start_job(job["job_id"])
        else:
            active_service.execute_job(job["job_id"])
        return job

    @app.get("/api/runs/{job_id}")
    async def get_run(job_id: str) -> dict:
        active_service = app.state.paper_summary_service
        job = active_service.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @app.get("/api/newspaper/latest")
    async def get_latest_newspaper() -> dict[str, str]:
        active_service = app.state.paper_summary_service
        newspaper = active_service.get_latest_newspaper()
        if newspaper is None:
            raise HTTPException(status_code=404, detail="No newspaper generated yet")
        return newspaper

    return app


app = create_app()


def main() -> None:
    """Run the web server with local development defaults."""

    uvicorn.run("backend.web.app:app", host="127.0.0.1", port=8000, reload=False)
