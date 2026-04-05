"""Mock HCP (Hynix Cloud Platform) roles API for local SSO testing."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Mock HCP Roles API")

PROJECT_ROLES = {
    "project-a": {
        "managers": ["EMP001"],
        "deployApprovers": ["EMP002"],
        "developers": ["EMP003", "EMP004", "EMP005"],
    },
    "project-b": {
        "managers": ["EMP001"],
        "deployApprovers": ["EMP002"],
        "developers": ["EMP006", "EMP007", "EMP008"],
    },
}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/v1/projects/{project_id}/roles")
async def get_roles(project_id: str):
    roles = PROJECT_ROLES.get(project_id, {"managers": [], "deployApprovers": [], "developers": []})
    return {"response": roles}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)
