"""Shared helpers for example analysis tools."""

from __future__ import annotations

import ast
import configparser
import math
import operator
from pathlib import Path
from typing import Any

import yaml


def load_prior_file(path: str) -> dict[str, Any]:
    """Load prior definitions from YAML or INI format."""
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise ValueError(
                "YAML prior file must parse to a mapping/dictionary"
            )
        return _normalise_numeric_expressions(data)

    if suffix == ".ini":
        parser = configparser.ConfigParser()
        parser.read(path)
        out: dict[str, Any] = {}
        for section in parser.sections():
            out[section] = {
                k: _coerce_numeric(v) for k, v in parser.items(section)
            }
        return _normalise_numeric_expressions(out)

    raise ValueError("Unsupported prior file type. Use .yaml/.yml or .ini")


def _coerce_numeric(value: str) -> float | str:
    try:
        return float(value)
    except ValueError:
        return _parse_numeric_expression(value)


def _normalise_numeric_expressions(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalise_numeric_expressions(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalise_numeric_expressions(item) for item in value]
    if isinstance(value, str):
        return _parse_numeric_expression(value)
    return value


def _parse_numeric_expression(value: str) -> float | str:
    """Parse numeric strings, including simple expressions with pi.

    Supported examples: "3.14", "pi", "-pi", "0.5*pi", "pi/2".
    Returns original string if parsing is not possible.
    """
    text = value.strip()
    if not text:
        return value

    try:
        return float(text)
    except ValueError:
        pass

    try:
        node = ast.parse(text, mode="eval")
    except SyntaxError:
        return value

    binary_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    def _eval(expr: ast.AST) -> float:
        if isinstance(expr, ast.Expression):
            return _eval(expr.body)
        if isinstance(expr, ast.Constant) and isinstance(
            expr.value, (int, float)
        ):
            return float(expr.value)
        if isinstance(expr, ast.UnaryOp) and isinstance(
            expr.op, (ast.UAdd, ast.USub)
        ):
            val = _eval(expr.operand)
            return val if isinstance(expr.op, ast.UAdd) else -val
        if isinstance(expr, ast.BinOp) and type(expr.op) in binary_ops:
            left = _eval(expr.left)
            right = _eval(expr.right)
            return float(binary_ops[type(expr.op)](left, right))
        if isinstance(expr, ast.Name) and expr.id == "pi":
            return float(math.pi)
        raise ValueError("Unsupported expression")

    try:
        return _eval(node)
    except (ValueError, ZeroDivisionError):
        return value


def get_param_prior(priors: dict[str, Any], name: str) -> dict[str, Any]:
    """Return a normalized prior dictionary for a named parameter."""
    spec = priors.get(name, {})

    if isinstance(spec, (int, float)):
        return {"value": float(spec)}

    if isinstance(spec, dict):
        out = dict(spec)
        if "value" in out:
            out["value"] = float(out["value"])
        if "min" in out:
            out["min"] = float(out["min"])
        if "max" in out:
            out["max"] = float(out["max"])
        return out

    return {}


def apply_bounds(value: float, prior: dict[str, Any]) -> float:
    """Clip *value* by [min, max] if those bounds are present in *prior*."""
    if "min" in prior:
        value = max(value, float(prior["min"]))
    if "max" in prior:
        value = min(value, float(prior["max"]))
    return value
