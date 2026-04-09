#!/usr/bin/env python
"""Generate a basic iterative GWAITH workflow as bash scripts.

Per round:
1. Estimate noise (PSD)
2. Run module jobs in parallel (interchangeable tools)
3. Subtract all produced module signals from the round input data

After all rounds:
- consolidate parameter files into one YAML
- estimate final noise from the final residual
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import yaml

from gwaith import add_gwaith_common_options, init_logging
from gwaith.config import load_config, normalise_config

logger = logging.getLogger("gwaith.workflow.build")


def _script_header() -> str:
    return "#!/usr/bin/env bash\nset -euo pipefail\n\n"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    mode = path.stat().st_mode
    path.chmod(mode | 0o111)


def _round_tag(round_index: int) -> str:
    return f"round_{round_index:03d}"


def _noise_script(
    round_dir: Path,
    round_index: int,
    data_in: str,
    data_dataset: str,
    estimate_psd_cmd: str,
) -> tuple[Path, str]:
    round_tag = _round_tag(round_index)
    noise_file = round_dir / f"{round_tag}_noise.h5"
    script = round_dir / f"{round_tag}_job_noise_estimate.sh"
    content = _script_header() + (
        f'{estimate_psd_cmd} \\\n'
        f'  --data "{data_in}" \\\n'
        f'  --data-dataset "{data_dataset}" \\\n'
        f'  --output "{noise_file}" \\\n'
        '  --output-dataset "psd"\n'
    )
    _write_executable(script, content)
    return script, str(noise_file)


def _module_script(
    round_dir: Path,
    round_index: int,
    module: dict,
    data_in: str,
    data_dataset: str,
) -> tuple[Path, str, str]:
    round_tag = _round_tag(round_index)
    module_name = module["name"]
    executable = module["executable"]
    priors = module.get("priors")
    signal_dataset = module.get("signal_dataset", "signal")

    output_signal = round_dir / f"{round_tag}_{module_name}_signal.h5"
    output_params = round_dir / f"{round_tag}_{module_name}_params.yaml"
    script = round_dir / f"{round_tag}_job_fit_{module_name}.sh"

    lines = [
        _script_header(),
        f'{executable} \\\n',
        f'  --data "{data_in}" \\\n',
        f'  --data-dataset "{data_dataset}" \\\n',
    ]
    if priors:
        lines.append(f'  --priors "{priors}" \\\n')
    lines.extend(
        [
            f'  --output-signal "{output_signal}" \\\n',
            f'  --output-signal-dataset "{signal_dataset}" \\\n',
            f'  --output-params "{output_params}"\n',
        ]
    )

    _write_executable(script, "".join(lines))
    return script, str(output_signal), str(output_params)


def _subtract_script(
    round_dir: Path,
    round_index: int,
    data_in: str,
    data_dataset: str,
    signal_inputs: list[dict[str, str]],
) -> tuple[Path, str]:
    round_tag = _round_tag(round_index)
    output_residual = round_dir / f"{round_tag}_combined_residual.h5"
    script = round_dir / f"{round_tag}_job_subtract_signals.sh"

    signal_files = [s["file"] for s in signal_inputs]
    signal_datasets = [s["dataset"] for s in signal_inputs]

    lines = [_script_header()]
    lines.extend(
        [
            "if command -v gwaith_subtract_signals >/dev/null 2>&1; then\n",
            "  CMD=(gwaith_subtract_signals)\n",
            "else\n",
            "  CMD=(python3 -m gwaith.tools.subtraction.subtract_signals)\n",
            "fi\n\n",
            '"${CMD[@]}" \\\n',
            f'  --data "{data_in}" \\\n',
            f'  --data-dataset "{data_dataset}" \\\n',
        ]
    )
    for sig_file in signal_files:
        lines.append(f'  --signal "{sig_file}" \\\n')
    for sig_dataset in signal_datasets:
        lines.append(f'  --signal-dataset "{sig_dataset}" \\\n')
    lines.extend(
        [
            f'  --output "{output_residual}" \\\n',
            '  --output-dataset "data"\n',
        ]
    )
    content = "".join(lines)
    _write_executable(script, content)
    return script, str(output_residual)


def _per_module_input_script(
    round_dir: Path,
    round_index: int,
    module: dict,
    base_data: str,
    base_dataset: str,
    other_signals: list[dict[str, str]],
) -> tuple[Path, str]:
    """Create per-module input data by subtracting all OTHER modules' latest signals."""
    round_tag = _round_tag(round_index)
    module_name = module["name"]
    output_data = round_dir / f"{round_tag}_{module_name}_input_data.h5"
    script = round_dir / f"{round_tag}_job_prep_{module_name}_data.sh"

    if not other_signals:
        content = _script_header() + f'cp "{base_data}" "{output_data}"\n'
        _write_executable(script, content)
        return script, str(output_data)

    signal_files = [s["file"] for s in other_signals]
    signal_datasets = [s["dataset"] for s in other_signals]

    lines = [_script_header()]
    lines.extend(
        [
            "if command -v gwaith_subtract_signals >/dev/null 2>&1; then\n",
            "  CMD=(gwaith_subtract_signals)\n",
            "else\n",
            "  CMD=(python3 -m gwaith.tools.subtraction.subtract_signals)\n",
            "fi\n\n",
            '"${CMD[@]}" \\\n',
            f'  --data "{base_data}" \\\n',
            f'  --data-dataset "{base_dataset}" \\\n',
        ]
    )
    for sig_file in signal_files:
        lines.append(f'  --signal "{sig_file}" \\\n')
    for sig_dataset in signal_datasets:
        lines.append(f'  --signal-dataset "{sig_dataset}" \\\n')
    lines.extend(
        [
            f'  --output "{output_data}" \\\n',
            '  --output-dataset "data"\n',
        ]
    )
    content = "".join(lines)
    _write_executable(script, content)
    return script, str(output_data)


def _finalize_consolidate_script(
    final_dir: Path,
    final_round: int,
    final_round_param_files: list[dict[str, str]],
) -> Path:
    script = final_dir / "finalize_job_consolidate_params.sh"
    output_file = final_dir / "final_consolidated_params.yaml"

    lines = [_script_header()]
    lines.extend(
        [
            "if command -v gwaith_consolidate_params >/dev/null 2>&1; then\n",
            "  CMD=(gwaith_consolidate_params)\n",
            "else\n",
            "  CMD=(python3 -m gwaith.tools.workflow.consolidate_params)\n",
            "fi\n\n",
            "\"${CMD[@]}\" \\\n",
            f"  --round {final_round} \\\n",
        ]
    )
    for entry in final_round_param_files:
        lines.append(f'  --module-param "{entry["name"]}={entry["path"]}" \\\n')
    lines.append(f'  --output "{output_file}"\n')

    content = "".join(lines)
    _write_executable(script, content)
    return script


def _finalize_noise_script(
    final_dir: Path,
    final_residual: str,
    estimate_psd_cmd: str,
) -> tuple[Path, str]:
    script = final_dir / "finalize_job_final_noise_estimate.sh"
    final_noise = final_dir / "final_noise_estimate.h5"

    content = _script_header() + (
        f'{estimate_psd_cmd} \\\n'
        f'  --data "{final_residual}" \\\n'
        '  --data-dataset "data" \\\n'
        f'  --output "{final_noise}" \\\n'
        '  --output-dataset "psd"\n'
    )
    _write_executable(script, content)
    return script, str(final_noise)


def _master_script(workflow_dir: Path, rounds: int, module_names: list[str]) -> Path:
    script = workflow_dir / "run_workflow.sh"
    lines = [_script_header()]

    for r in range(1, rounds + 1):
        round_tag = _round_tag(r)
        round_dir = workflow_dir / round_tag
        noise = round_dir / f"{round_tag}_job_noise_estimate.sh"
        subtract = round_dir / f"{round_tag}_job_subtract_signals.sh"

        lines.append(f'echo "Running {round_tag} noise estimate"\n')
        lines.append(f'bash "{noise}"\n')

        if r > 1:
            lines.append(f'echo "Preparing per-module input data for {round_tag}"\n')
            for name in module_names:
                prep = round_dir / f"{round_tag}_job_prep_{name}_data.sh"
                lines.append(f'bash "{prep}" &\n')
            lines.append('wait\n')

        lines.append(f'echo "Running {round_tag} module jobs in parallel"\n')

        for name in module_names:
            job = round_dir / f"{round_tag}_job_fit_{name}.sh"
            lines.append(f'bash "{job}" &\n')

        lines.append('wait\n')
        lines.append(f'echo "Combining residuals for {round_tag}"\n')
        lines.append(f'bash "{subtract}"\n\n')

    lines.append('echo "Final consolidation and noise estimate"\n')
    lines.append(f'bash "{workflow_dir / "final" / "finalize_job_consolidate_params.sh"}"\n')
    lines.append(f'bash "{workflow_dir / "final" / "finalize_job_final_noise_estimate.sh"}"\n')

    _write_executable(script, "".join(lines))
    return script


def build_workflow(config_path: Path) -> dict:
    cfg = normalise_config(load_config(config_path), config_type="workflow")

    workflow_name = cfg["workflow"]["name"]
    rounds = int(cfg["workflow"]["rounds"])
    workflow_dir = Path(cfg["workflow"]["output_dir"]).expanduser().resolve() / workflow_name
    workflow_dir.mkdir(parents=True, exist_ok=True)

    input_data = cfg["input"]["data_file"]
    input_dataset = cfg["input"]["data_dataset"]

    estimate_psd_cmd = cfg["executables"]["estimate_psd"]
    modules = cfg["modules"]

    round_manifests: list[dict] = []
    final_round_param_files: list[dict[str, str]] = []

    # combined residual of the previous round (used for noise estimate)
    current_data = input_data
    current_dataset = input_dataset

    # latest signal outputs per module, keyed by module name
    prev_round_signals: dict[str, dict[str, str]] = {}

    for r in range(1, rounds + 1):
        round_tag = _round_tag(r)
        round_dir = workflow_dir / round_tag
        round_dir.mkdir(parents=True, exist_ok=True)

        noise_script, noise_file = _noise_script(
            round_dir=round_dir,
            round_index=r,
            data_in=current_data,
            data_dataset=current_dataset,
            estimate_psd_cmd=estimate_psd_cmd,
        )

        # Build per-module input-data prep scripts for rounds > 1.
        # Each module receives the original data with all OTHER modules' latest
        # signals subtracted so it refits against its own clean residual.
        prep_scripts: dict[str, dict[str, str]] = {}
        if r > 1:
            for module in modules:
                other_signals = [
                    prev_round_signals[m["name"]]
                    for m in modules
                    if m["name"] != module["name"] and m["name"] in prev_round_signals
                ]
                prep_script, mod_data_file = _per_module_input_script(
                    round_dir=round_dir,
                    round_index=r,
                    module=module,
                    base_data=input_data,
                    base_dataset=input_dataset,
                    other_signals=other_signals,
                )
                prep_scripts[module["name"]] = {
                    "script": str(prep_script),
                    "data_file": mod_data_file,
                    "data_dataset": "data",
                }

        module_jobs: list[dict[str, str]] = []
        signal_inputs: list[dict[str, str]] = []
        for module in modules:
            if module["name"] in prep_scripts:
                mod_data_in = prep_scripts[module["name"]]["data_file"]
                mod_data_dataset = "data"
            else:
                mod_data_in = input_data
                mod_data_dataset = input_dataset

            module_script, signal_file, params_file = _module_script(
                round_dir=round_dir,
                round_index=r,
                module=module,
                data_in=mod_data_in,
                data_dataset=mod_data_dataset,
            )
            module_jobs.append(
                {
                    "name": module["name"],
                    "script": str(module_script),
                    "signal_file": signal_file,
                    "signal_dataset": module.get("signal_dataset", "signal"),
                    "params_file": params_file,
                }
            )
            signal_inputs.append(
                {
                    "file": signal_file,
                    "dataset": module.get("signal_dataset", "signal"),
                }
            )
            if r == rounds:
                final_round_param_files.append({
                    "name": module["name"],
                    "path": params_file,
                })

        # Combined residual always computed from original data minus all current-round
        # signals.  This gives the true residual for the noise estimate.
        subtract_script, combined_residual = _subtract_script(
            round_dir=round_dir,
            round_index=r,
            data_in=input_data,
            data_dataset=input_dataset,
            signal_inputs=signal_inputs,
        )

        round_manifests.append(
            {
                "round": r,
                "noise_script": str(noise_script),
                "noise_file": noise_file,
                "prep_scripts": prep_scripts,
                "module_jobs": module_jobs,
                "subtract_script": str(subtract_script),
                "round_residual": combined_residual,
            }
        )

        prev_round_signals = {
            job["name"]: {"file": job["signal_file"], "dataset": job["signal_dataset"]}
            for job in module_jobs
        }
        current_data = combined_residual
        current_dataset = "data"

    final_dir = workflow_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)

    consolidate_script = _finalize_consolidate_script(
        final_dir=final_dir,
        final_round=rounds,
        final_round_param_files=final_round_param_files,
    )
    final_noise_script, final_noise = _finalize_noise_script(
        final_dir=final_dir,
        final_residual=current_data,
        estimate_psd_cmd=estimate_psd_cmd,
    )

    module_names = [m["name"] for m in modules]
    master = _master_script(workflow_dir, rounds, module_names)

    manifest = {
        "workflow": cfg["workflow"],
        "input": cfg["input"],
        "modules": modules,
        "rounds": round_manifests,
        "final": {
            "consolidate_script": str(consolidate_script),
            "final_noise_script": str(final_noise_script),
            "final_residual": current_data,
            "final_noise": final_noise,
            "consolidated_params": str(final_dir / "final_consolidated_params.yaml"),
        },
        "master_script": str(master),
    }

    manifest_path = workflow_dir / "workflow_manifest.yaml"
    with manifest_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, sort_keys=False)

    return {
        "workflow_dir": str(workflow_dir),
        "manifest": str(manifest_path),
        "master_script": str(master),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gwaith_build_workflow",
        description="Generate iterative GWAITH workflow bash scripts from YAML config.",
    )
    parser.add_argument("--config", required=True, help="Path to workflow config YAML")
    add_gwaith_common_options(parser)
    args = parser.parse_args(argv)

    init_logging(args.verbose)
    result = build_workflow(Path(args.config))
    logger.info("Workflow created in: %s", result["workflow_dir"])
    logger.info("Manifest: %s", result["manifest"])
    logger.info("Run with: %s", result["master_script"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
