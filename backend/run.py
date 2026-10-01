"""
DataLens AI — Production Application Runner.

Reads PORT and HOST from environment variables (e.g. Render, Railway, Fly.io)
and starts the Uvicorn ASGI server.
"""

import os
import uvicorn
from app.config import HOST, PORT

if __name__ == "__main__":
    port = int(os.getenv("PORT", str(PORT)))
    host = os.getenv("HOST", HOST)
    print(f"Starting DataLens AI server on {host}:{port}...")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
