"""Configuration normalisation helpers for GWAITH."""

from __future__ import annotations

from typing import Any


def normalise_config(
    raw: dict[str, Any], config_type: str | None = None
) -> dict[str, Any]:
    """Normalise configuration using a generic dispatcher.

    Parameters
    ----------
    raw:
        Raw configuration mapping loaded from file.
    config_type:
        Optional explicit config type. Supported values:
        - ``"workflow"``

    Returns
    -------
    dict[str, Any]
        Normalised configuration dictionary.
    """
    if not isinstance(raw, dict):
        raise ValueError("Config must be a mapping")

    if config_type is None:
        if "workflow" in raw and "input" in raw:
            config_type = "workflow"
        else:
            raise ValueError(
                "Could not infer config type. Provide config_type as " "'workflow'."
            )

    if config_type == "workflow":
        return normalise_workflow_config(raw)

    raise ValueError(
        f"Unsupported config_type: {config_type!r}. " "Supported values: 'workflow'"
    )


def normalise_workflow_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise workflow config to a standard internal format.

    Returned structure:
    {
      "workflow": {
        "name": str,
        "rounds": int,
        "output_dir": str,
      },
      "input": {
        "data_file": str,
        "data_dataset": str,
      },
      "executables": {
        "estimate_psd": str,
      },
      "modules": [
        {
          "name": str,
          "executable": str,
          "priors": str | None,
          "signal_dataset": str,
        },
        ...
      ],
    }
    """
    workflow = raw.get("workflow", {})
    if not isinstance(workflow, dict):
        raise ValueError("'workflow' must be a mapping")

    input_cfg = raw.get("input", {})
    if not isinstance(input_cfg, dict):
        raise ValueError("'input' must be a mapping")

    executables = raw.get("executables", {})
    if not isinstance(executables, dict):
        raise ValueError("'executables' must be a mapping")

    modules_raw = raw.get("modules")
    priors = raw.get("priors", {})
    if modules_raw is None and priors and not isinstance(priors, dict):
        raise ValueError("'priors' must be a mapping")

    rounds = int(workflow.get("rounds", 3))
    if rounds < 1:
        raise ValueError("workflow.rounds must be >= 1")

    data_file = input_cfg.get("data_file")
    if not data_file:
        raise ValueError("input.data_file is required")

    modules: list[dict[str, Any]] = []

    # New generalised format: modules list.
    if modules_raw is not None:
        if not isinstance(modules_raw, list) or not modules_raw:
            raise ValueError("'modules' must be a non-empty list")
        for mod in modules_raw:
            if not isinstance(mod, dict):
                raise ValueError("Each module entry must be a mapping")
            name = mod.get("name")
            executable = mod.get("executable")
            if not name or not executable:
                raise ValueError("Each module requires 'name' and 'executable'")
            modules.append(
                {
                    "name": str(name),
                    "executable": str(executable),
                    "priors": (
                        str(mod["priors"])
                        if "priors" in mod and mod["priors"]
                        else None
                    ),
                    "signal_dataset": str(mod.get("signal_dataset", "signal")),
                }
            )
    else:
        # Backward-compatible format: priors + executables for offset/sine.
        if not isinstance(priors, dict):
            raise ValueError("'priors' must be a mapping")
        offset_prior = priors.get("offset")
        sine_prior = priors.get("sine")
        if not offset_prior or not sine_prior:
            raise ValueError(
                "Either provide 'modules', or provide priors.offset and priors.sine"
            )
        modules = [
            {
                "name": "offset",
                "executable": str(executables.get("fit_offset", "gwaith_fit_offset")),
                "priors": str(offset_prior),
                "signal_dataset": "signal",
            },
            {
                "name": "sine",
                "executable": str(executables.get("fit_sine", "gwaith_fit_sine")),
                "priors": str(sine_prior),
                "signal_dataset": "signal",
            },
        ]

    return {
        "workflow": {
            "name": str(workflow.get("name", "gwaith_workflow")),
            "rounds": rounds,
            "output_dir": str(workflow.get("output_dir", "workflow_out")),
        },
        "input": {
            "data_file": str(data_file),
            "data_dataset": str(input_cfg.get("data_dataset", "data")),
        },
        "executables": {
            "estimate_psd": str(executables.get("estimate_psd", "gwaith_estimate_psd")),
        },
        "modules": modules,
    }
