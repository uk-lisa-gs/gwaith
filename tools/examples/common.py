"""Shared helpers for example analysis tools."""

from __future__ import annotations

import configparser
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
        return data

    if suffix == ".ini":
        parser = configparser.ConfigParser()
        parser.read(path)
        out: dict[str, Any] = {}
        for section in parser.sections():
            out[section] = {
                k: _coerce_numeric(v) for k, v in parser.items(section)
            }
        return out

    raise ValueError("Unsupported prior file type. Use .yaml/.yml or .ini")


def _coerce_numeric(value: str) -> float | str:
    try:
        return float(value)
    except ValueError:
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
