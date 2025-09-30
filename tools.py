from typing import Any, Dict, List, Tuple


class CalcError(ValueError):
    pass


def calculate_from_dict(d: Dict[str, Any]) -> Tuple[float, str, List[float]]:
    """
    Processes a calculation based on the OpenAPI schema from calculator.txt.
    Expects: {"operand1": 10, "operand2": 5, "operation": "+"} 

    Returns: (result, op, operands)
    """
    if not isinstance(d, dict):
        raise CalcError("JSON payload must be an object.")

    required_keys = {"operand1", "operand2", "operation"}
    if not required_keys.issubset(d.keys()):
        missing = required_keys - d.keys()
        raise CalcError(f"Missing required keys: {', '.join(missing)}")

    try:
        operand1 = float(d["operand1"])
        operand2 = float(d["operand2"])
        operands = [operand1, operand2]
    except (ValueError, TypeError) as e:
        raise CalcError(f"Operands must be numbers: {e}") from e

    op = str(d["operation"])

    if op == "+":
        result = operand1 + operand2
    elif op == "-":
        result = operand1 - operand2
    elif op == "*":
        result = operand1 * operand2
    elif op == "/":
        if operand2 == 0:
            raise CalcError("Division by zero.")
        result = operand1 / operand2
    else:
        raise CalcError(f"Unsupported operation '{op}'. Use one of: +, -, *, /") [cite: 9]

    return float(result), op, operands