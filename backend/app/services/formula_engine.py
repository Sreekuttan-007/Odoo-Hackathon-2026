"""A constrained, AST-based expression evaluator for FORMULA salary rules.

This is NOT eval()/exec() — it walks a whitelist of AST node types and
resolves names only against an explicitly-provided context dict. There is
no attribute access, no function calls, no imports, no comprehensions, no
lambdas — so there is no path to builtins, the filesystem, or the network
regardless of what an admin types into a rule's formula field.

Supported syntax: numeric literals, +, -, *, /, %, **, unary +/-,
parentheses, plain names resolved from `context`, and `rules["CODE"]` /
`categories["CATEGORY"]` subscripts with a string literal key.
"""
import ast
import operator
from decimal import Decimal, InvalidOperation
from typing import Any


class FormulaError(ValueError):
    pass


_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_SUBSCRIPTABLE_NAMES = {"rules", "categories"}


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise FormulaError(f"Value is not numeric: {value!r}")


def evaluate_formula(expression: str, context: dict) -> Decimal:
    """Evaluates a formula string against context and returns a Decimal.
    Raises FormulaError on invalid syntax, disallowed constructs, or an
    unresolvable name/key."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"Invalid formula syntax: {exc.msg}")
    return _eval_node(tree.body, context)


def _eval_node(node: ast.AST, context: dict) -> Decimal:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise FormulaError("Only numeric literals are allowed.")
        return Decimal(str(node.value))

    if isinstance(node, ast.Name):
        if node.id not in context:
            raise FormulaError(f"Unknown variable: {node.id}")
        return _to_decimal(context[node.id])

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINOPS:
            raise FormulaError(f"Operator not allowed: {op_type.__name__}")
        left = _eval_node(node.left, context)
        right = _eval_node(node.right, context)
        try:
            return _BINOPS[op_type](left, right)
        except (ZeroDivisionError, InvalidOperation) as exc:
            raise FormulaError(f"Arithmetic error: {exc}")

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARYOPS:
            raise FormulaError(f"Operator not allowed: {op_type.__name__}")
        return _UNARYOPS[op_type](_eval_node(node.operand, context))

    if isinstance(node, ast.Subscript):
        if not (isinstance(node.value, ast.Name) and node.value.id in _SUBSCRIPTABLE_NAMES):
            raise FormulaError("Only rules[\"CODE\"] and categories[\"CATEGORY\"] subscripts are allowed.")
        container_name = node.value.id
        if container_name not in context:
            raise FormulaError(f"Unknown variable: {container_name}")
        container = context[container_name]

        key_node = node.slice
        if isinstance(key_node, ast.Index):  # pragma: no cover - py<3.9 compat
            key_node = key_node.value
        if not (isinstance(key_node, ast.Constant) and isinstance(key_node.value, str)):
            raise FormulaError("Subscript key must be a string literal.")
        key = key_node.value
        if key not in container:
            raise FormulaError(f"Unknown {'rule code' if container_name == 'rules' else 'category'}: {key}")
        return _to_decimal(container[key])

    raise FormulaError(f"Expression construct not allowed: {type(node).__name__}")
