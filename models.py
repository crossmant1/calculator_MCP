from typing import Optional, Any, Dict, List
from pydantic import BaseModel, HttpUrl, model_validator


class CalculateRequest(BaseModel):
    """
    Accepts either an inline JSON object or a URL pointing to a JSON file.
    """
    json: Optional[Dict[str, Any]] = None
    json_url: Optional[HttpUrl] = None

    @model_validator(mode="after")
    def check_one_of(cls, values):
        has_inline = values.json is not None
        has_url = values.json_url is not None
        if has_inline == has_url:  # both True or both False
            raise ValueError("Provide exactly one of 'json' or 'json_url'.")
        return values


class CalculateResponse(BaseModel):
    result: float
    op: str
    operands: List[float]
