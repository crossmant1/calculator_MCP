import os
import json
import httpx
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import AnyHttpUrl
from typing import Dict, Optional, AsyncGenerator
from tools import calculate_from_dict, CalcError

# Environment variables for security
API_KEY = os.getenv("API_KEY")
ALLOWED_ORIGINS = set(os.getenv("ALLOWED_ORIGINS", "").split(",")) if os.getenv("ALLOWED_ORIGINS") else None

# Initialize FastAPI app
app = FastAPI(title="Calculator MCP (Render)", version="1.0.0")

# Health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

# MCP calculate tool logic (same as original)
async def mcp_calculate(json: Optional[Dict] = None, json_url: Optional[AnyHttpUrl] = None) -> str:
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

# MCP endpoint for POST requests
@app.post("/mcp")
async def mcp_post(request: Request):
    try:
        # Parse the incoming MCP request
        body = await request.json()
        tool = body.get("tool")
        params = body.get("params", {})

        # Validate tool
        if tool != "calculate":
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool}")

        # Dispatch to calculate tool
        try:
            result = await mcp_calculate(
                json=params.get("json"),
                json_url=params.get("json_url")
            )
            # Return MCP-compatible response
            return {"status": "success", "result": json.loads(result)}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Optional: MCP endpoint for SSE (GET) if streaming is needed
@app.get("/mcp")
async def mcp_get(request: Request) -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[str, None]:
        # Placeholder for SSE streaming (if required)
        yield "data: {\"status\": \"streaming not implemented\"}\n\n"
        # Add actual streaming logic here if needed
        # For example, you could stream calculation results or updates
    return StreamingResponse(event_stream(), media_type="text/event-stream")

# Security middleware for /mcp endpoint
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
