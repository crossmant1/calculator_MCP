import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import httpx

# These imports assume your files are in the same directory.
# If you place them in an 'app' sub-directory, the imports would be:
# from app.models import CalculateRequest, CalculateResponse
# from app.tools import calculate_from_dict, CalcError
from models import CalculateRequest, CalculateResponse
from tools import calculate_from_dict, CalcError


app = FastAPI(title="MCP Calculator Tool", version="1.0.0")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/tools/calculate", response_model=CalculateResponse)
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
    except Exception:
        # FIX: Added a proper response for unexpected errors to resolve the IndentationError.
        raise HTTPException(status_code=500, detail="An unexpected internal server error occurred.")
