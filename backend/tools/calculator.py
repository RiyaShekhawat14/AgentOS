import ast
import math
import operator
import statistics

from backend.tools.base import Tool, ToolContext, ToolError

_BINARY = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "sqrt": math.sqrt, "abs": abs, "round": round, "min": min, "max": max,
    "sum": sum, "mean": statistics.fmean, "log": math.log, "log10": math.log10,
    "exp": math.exp, "floor": math.floor, "ceil": math.ceil,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}
MAX_LENGTH = 500
MAX_EXPONENT = 1000


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(item) for item in node.elts]
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
            raise ToolError("Exponent is too large.")
        return _BINARY[type(node.op)](left, right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in _FUNCTIONS and not node.keywords:
        return _FUNCTIONS[node.func.id](*[_eval(a) for a in node.args])
    raise ToolError("Only numbers, + - * / // % **, brackets and functions "
                    f"({', '.join(_FUNCTIONS)}) are allowed.")


def run(args: dict, ctx: ToolContext):
    expression = str(args.get("expression", "")).strip()
    if not expression:
        raise ToolError("Give a maths expression in 'expression'.")
    if len(expression) > MAX_LENGTH:
        raise ToolError("Expression is too long.")
    try:
        value = _eval(ast.parse(expression, mode="eval").body)
    except ToolError:
        raise
    except ZeroDivisionError:
        raise ToolError("Division by zero.")
    except (SyntaxError, ValueError, TypeError, OverflowError) as e:
        raise ToolError(f"Could not calculate this expression: {e}")
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ToolError("The result is not a finite number.")
    return {"expression": expression, "result": value}


TOOL = Tool(
    name="calculator",
    description="Do exact maths: arithmetic, percentages, KPIs. Never calculate in your head.",
    args={"expression": "maths expression, for example (1200 * 0.18) + 50 or mean([3, 5, 9])"},
    run=run,
)
