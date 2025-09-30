import os
import httpx
from fastapi import FastAPI, HTTPException, Security, Depends, status
from fastapi.security import APIKeyHeader

# These imports remain the same
from models import CalculateRequest, CalculateResponse
from tools import calculate_from_dict, CalcError

# --- New Security Setup ---

# This defines the name of the header we will be looking for.
api_key_header = APIKeyHeader(name="X-API-Key")

# This is our secret key. We will get it from an environment variable.
# It's very important NOT to write the actual key in the code.
API_KEY = os.getenv("API_KEY")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Dependency function to validate the API key from the X-API-Key header.
    """
    if not API_KEY:
        # This handles the case where the server admin hasn't set the key.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API Key not configured on server",
        )
    if api_key_header == API_KEY:
        return api_key_header
    else:
        # This is the error a bad client will get.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )


# --- FastAPI App ---

app = FastAPI(title="MCP Calculator Tool", version="1.0.0")


@app.get("/healthz", dependencies=[Depends(get_api_key)])
async def healthz():
    return {"status": "ok"}


# --- Modified Endpoint ---
# Notice the new `dependencies=[Depends(get_api_key)]` argument.
# This tells FastAPI to run our get_api_key function before running the main logic.
@app.post(
    "/tools/calculate",
    response_model=CalculateResponse,
    dependencies=[Depends(get_api_key)],
)
async def calculate(req: CalculateRequest):
    # Fetch JSON if a URL was provided; otherwise use inline JSON.
    if req.json_url:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(str(req.json_url))
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch JSON: {e}")
    else:
        data = req.json

    try:
        result, op, operands = calculate_from_dict(data)
        return CalculateResponse(result=result, op=op, operands=operands)
    except CalcError as e:
        raise HTTPException(status_code=400, detail=str(e))


