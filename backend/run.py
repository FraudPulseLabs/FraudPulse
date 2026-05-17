"""Dev entrypoint: `python run.py` from the `backend/` directory."""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=["src/db/models/base.py"] # Exclude the problematic file
    )
