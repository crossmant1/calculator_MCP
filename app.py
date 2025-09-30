# app.py
import os
import json
import httpx
from fastapi import FastAPI, Request, status
from starlette.responses import JSONResponse
from pydantic import AnyHttpUrl
from mcp.server.fastmcp import FastMCP

# Your existing calculator logic
from tools import calculate_from_dict, CalcError

API_KEY = os.getenv("API_KEY")
# Optional: comma-separated list of allowed Origins (leave unset to skip Origin check)
ALLOWED_ORIGINS = set(os.getenv("ALLOWED_ORIGINS", "").split(",")) if os.getenv("ALLOWED_ORIGINS") else None

app = FastAPI(title="Calculator MCP (Render)", version="1.0.0")

# Public health for Render (no auth)
@app.get("/health")
def health():
    return {"status": "ok"}

# --- MCP server (Streamable HTTP) ---
mcp = FastMCP("calculator-mcp", stateless_http=True)

@mcp.tool(
    "calculate",
    description="Compute result from a JSON object or a URL pointing to JSON with fields 'op' and 'operands'.",
)
async def mcp_calculate(
    json: dict | None = None,
    json_url: AnyHttpUrl | None = None,
) -> str:
    """
    Returns a JSON string: {"result": <number>, "op": <str>, "operands": <list>}
    """
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

# Obtain the Streamable HTTP ASGI app from the SDK (fallback for older versions)
try:
    mcp_app = mcp.streamable_http_app()
except AttributeError:
    # Older SDKs exposed SSE app; MCP spec now prefers Streamable HTTP,
    # but this keeps backward compatibility.
    mcp_app = mcp.sse_app()

# Security middleware for the MCP path (/mcp)
@app.middleware("http")
async def mcp_security(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        # 1) API key check
        if not API_KEY:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "API Key not configured on server"},
            )
        provided = request.headers.get("x-api-key")
        if provided != API_KEY:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Could not validate credentials"},
            )

        # 2) Optional Origin validation (recommended by MCP transport guidance)
        if ALLOWED_ORIGINS is not None:
            origin = request.headers.get("origin")
            if not origin or origin not in ALLOWED_ORIGINS:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Origin not allowed"},
                )

    return await call_next(request)

# Mount the MCP server under /mcp
app.mount("/mcp", mcp_app)
