"""AuditPilot ADK Web Interface and Application Server."""

import os
from dotenv import load_dotenv

# Load local environment file if present (ignored in Docker by .dockerignore)
load_dotenv("auditpilot/.env")
load_dotenv(".env")

import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

APP_DIR = os.path.dirname(os.path.abspath(__file__))

app = get_fast_api_app(
    agents_dir=APP_DIR,
    allow_origins=["*"],
    web=True,
)


@app.get("/health")
def health():
    """Health check endpoint for container and deployment verification."""
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
