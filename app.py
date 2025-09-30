# app.py
import os
import json
import httpx
from fastapi import FastAPI, Request, status
from starlette.responses import JSONResponse
from pydantic import AnyHttpUrl
from mcp.server.fastmcp import FastMCP

from tools import calculate_from_dict, CalcError

API_KEY = os.getenv("API_KEY")
ALLOWED_ORIGINS = set(os.getenv("ALLOWED_ORIGINS", "").split(",")) if os.getenv("ALLOWED_ORIGINS") else None

app = FastAPI(title="Calculator MCP (Render)", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


# ✅ IMPORTANT: set streamable_http_path="/" so when we mount at "/mcp"
# the effective endpoint is exactly /mcp/ (not /mcp/mcp).
mcp = FastMCP("calculator-mcp", stateless_http=True, streamable_http_path="/")

@mcp.tool("calculate", description="Compute result from JSON or a JSON URL.")
async def mcp_calculate(json: dict | None = None, json_url: AnyHttpUrl | None = None) -> str:
    data = json
    if json_url:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(str(json_url))
            r.raise_for_status()
            data = r.json()
    if not data:
        raise ValueError("Provide 'json' or 'json_url'")
    try:
        result, op, operands = calculate_from_dict(data)
    except CalcError as e:
        raise ValueError(str(e))
    return json.dumps({"result": result, "op": op, "operands": operands})

# Create the Streamable HTTP ASGI app and mount it under /mcp
# (MCP transport = single endpoint that accepts POSTs; optional SSE via GET) 
# https://modelcontextprotocol.io/specification/2025-03-26/basic/transports
mcp_app = mcp.streamable_http_app()
app.mount("/mcp", mcp_app)

# Protect /mcp with X-API-Key and (optionally) Origin checks
@app.middleware("http")
async def mcp_security(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        if not API_KEY or request.headers.get("x-api-key") != API_KEY:
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Could not validate credentials"})
        if ALLOWED_ORIGINS is not None:
            origin = request.headers.get("origin")
            if not origin or origin not in ALLOWED_ORIGINS:
                return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Origin not allowed"})
    return await call_next(request)
