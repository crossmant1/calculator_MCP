import os
import json
import httpx
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AnyHttpUrl
from typing import Dict, Optional, AsyncGenerator
from tools import calculate_from_dict, CalcError

# Environment variables for security
API_KEY = os.getenv("API_KEY")

# Initialize FastAPI app
app = FastAPI(title="Calculator MCP (Render)", version="1.0.0")

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["x-api-key", "Content-Type", "Origin"],
)

# Health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

# MCP calculate tool logic
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
        body = await request.json()
        tool = body.get("tool")
        params = body.get("params", {})
        if tool != "calculate":
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool}")
        try:
            result = await mcp_calculate(
                json=params.get("json"),
                json_url=params.get("json_url")
            )
            return {"status": "success", "result": json.loads(result)}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# MCP endpoint for SSE (GET)
@app.get("/mcp")
async def mcp_get(request: Request) -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[str, None]:
        yield "data: {\"status\": \"streaming not implemented\"}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")

# Security middleware for /mcp endpoint (only x-api-key check)
@app.middleware("http")
async def mcp_security(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        if not API_KEY or request.headers.get("x-api-key") != API_KEY:
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Could not validate credentials"})
    return await call_next(request)
