"""Bash exporter for workflow generation."""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import yaml

from ..types import GwaithFile, GwaithNode, GwaithStream, GwaithWorkflow
from .exporter import GwaithExporter, GwaithExportResult

_ROUND_TAG_TEMPLATE = "round_{round_index:03d}"
_DEFAULT_DATASET = "data"
_DEFAULT_SIGNAL_DATASET = "signal"
_DEFAULT_PSD_DATASET = "psd"

# The controller script is written as a raw string to preserve bash syntax.
# It processes jobs from job_state.tsv, retrying failed jobs up to max_retries.
# When a job exhausts all retries, it stays in RETRY state so it can be
# retried on the next invocation of run_workflow.sh.
_CONTROLLER_SCRIPT = r"""#!/usr/bin/env bash
set -euo pipefail

# Change to the directory containing this script so relative paths work
cd "$(dirname "$0")"

STATE_FILE="job_state.tsv"

if [[ ! -f "$STATE_FILE" ]]; then
    echo "State file $STATE_FILE missing! Please generate the workflow first."
    exit 1
fi

ALL_DONE=true

# Read line by line. Using || [[ -n "$uid" ]] ensures we catch the last line even if there's no trailing newline
while IFS=$'\t' read -r uid status retries script_path || [[ -n "$uid" ]]; do
    if [[ -z "$uid" ]]; then
        continue
    fi

    if [[ "$status" == "DONE" ]]; then
        printf "%s\t%s\t%s\t%s\n" "$uid" "$status" "$retries" "$script_path" >> "${STATE_FILE}.tmp"
        continue
    fi

    if [[ "$status" == "RETRY" ]]; then
        # Attempt the job, decrementing retries on failure
        while [[ "$retries" -gt 0 ]]; do
            echo "Running job: $uid (Retries left: $retries)"

            # Temporarily disable exit-on-error to handle script failure gracefully
            set +e
            bash "$script_path"
            EXIT_CODE=$?
            set -e

            if [[ $EXIT_CODE -eq 0 ]]; then
                echo "Job $uid completed successfully."
                status="DONE"
                break
            else
                retries=$((retries - 1))
                echo "Job $uid failed with exit code $EXIT_CODE."
                if [[ "$retries" -gt 0 ]]; then
                    echo "Retrying..."
                else
                    # No retries left - reset to RETRY 3 for next script invocation
                    echo "No retries left for $uid. Resetting to RETRY 3 times."
                    status="RETRY"
                    retries=3
                    break
                fi
            fi
        done

        printf "%s\t%s\t%s\t%s\n" "$uid" "$status" "$retries" "$script_path" >> "${STATE_FILE}.tmp"

        # If the job didn't complete successfully, stop processing remaining jobs
        # so they can pick up where we left off next time run_workflow.sh is called
        if [[ "$status" != "DONE" ]]; then
            ALL_DONE=false
            break
        fi
    else
        # FAILED or other unknown status, just carry it over and stop
        printf "%s\t%s\t%s\t%s\n" "$uid" "$status" "$retries" "$script_path" >> "${STATE_FILE}.tmp"
        ALL_DONE=false
        break
    fi

done < "$STATE_FILE"

# Overwrite old state with updated states
mv "${STATE_FILE}.tmp" "$STATE_FILE"

if [[ "$ALL_DONE" == false ]]; then
    echo "Workflow stopped. Check $STATE_FILE for details."
    exit 1
else
    echo "All jobs completed successfully!"
fi
"""


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(value)).strip("_") or "item"


def _round_tag(round_index: int) -> str:
    return _ROUND_TAG_TEMPLATE.format(round_index=int(round_index))


def _script_header() -> str:
    return "#!/usr/bin/env bash\nset -euo pipefail\n\n"


def _write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def _render_command(command: list[str]) -> str:
    return shlex.join([str(part) for part in command]) + "\n"


def _file_lookup(workflow: GwaithWorkflow) -> dict[str, GwaithFile]:
    return {gwaith_file.uid: gwaith_file for gwaith_file in workflow.files}


def _node_lookup(workflow: GwaithWorkflow) -> dict[str, GwaithNode]:
    return {gwaith_node.uid: gwaith_node for gwaith_node in workflow.nodes}


def _serialise_file(gwaith_file: GwaithFile) -> dict[str, Any]:
    return {
        "uid": gwaith_file.uid,
        "path": gwaith_file.local_path,
        "final_path": gwaith_file.final_path,
        "dataset": gwaith_file.dataset,
        "kind": gwaith_file.kind,
        "stream": gwaith_file.stream,
        "round": gwaith_file.round_index,
        "produced_by": gwaith_file.produced_by,
        "used_by": list(gwaith_file.used_by),
        "retention_level": gwaith_file.retention_level,
    }


def _serialise_node(gwaith_node: GwaithNode) -> dict[str, Any]:
    return {
        "uid": gwaith_node.uid,
        "name": gwaith_node.name,
        "stream": gwaith_node.stream,
        "round": gwaith_node.round_index,
        "command": list(gwaith_node.command),
        "uses": list(gwaith_node.uses),
        "produces": list(gwaith_node.produces),
        "resources": dict(gwaith_node.resources),
    }


def _serialise_stream(gwaith_stream: GwaithStream) -> dict[str, Any]:
    return {
        "uid": gwaith_stream.uid,
        "name": gwaith_stream.name,
        "environment": gwaith_stream.environment,
        "decimation": gwaith_stream.decimation,
        "skip_rounds": list(gwaith_stream.skip_rounds),
        "nodes": list(gwaith_stream.nodes),
    }


class GwaithBashExporter(GwaithExporter):
    """Exporter that writes bash scripts and a manifest."""

    def export(
        self, workflow: GwaithWorkflow, workflow_dir: Path
    ) -> GwaithExportResult:
        workflow_dir.mkdir(parents=True, exist_ok=True)
        node_scripts = self._write_node_scripts(workflow, workflow_dir)
        finalize_scripts = self._write_finalize_scripts(workflow, workflow_dir)
        master_script = self._write_master_script(
            workflow, workflow_dir, node_scripts, finalize_scripts
        )
        manifest = self._write_manifest(
            workflow, workflow_dir, node_scripts, finalize_scripts, master_script
        )
        return GwaithExportResult(
            manifest=manifest,
            master_script=master_script,
            node_scripts=node_scripts,
            finalize_scripts=finalize_scripts,
        )

    def _write_node_scripts(
        self, workflow_graph: GwaithWorkflow, workflow_dir: Path
    ) -> dict[str, str]:
        script_paths: dict[str, str] = {}
        for node in workflow_graph.nodes:
            if node.round_index is None:
                script_dir = workflow_dir / "final" / "scripts"
            else:
                script_dir = workflow_dir / _round_tag(node.round_index) / "scripts"
            script_path = script_dir / f"{_safe_name(node.name)}.sh"
            _write_executable(
                script_path, _script_header() + _render_command(node.command)
            )
            script_paths[node.uid] = str(script_path)
        return script_paths

    def _write_finalize_scripts(
        self, workflow_graph: GwaithWorkflow, workflow_dir: Path
    ) -> dict[str, str]:
        final_dir = workflow_dir / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        scripts: dict[str, str] = {}
        scripts_dir = final_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        file_by_uid = _file_lookup(workflow_graph)

        consolidate_path = scripts_dir / "finalize_consolidate_params.sh"
        consolidated_output = final_dir / "final_consolidated_params.yaml"
        module_params: list[str] = []
        for stream_uid, file_uid in workflow_graph.final_params.items():
            if file_uid is None:
                continue
            module_params.extend(
                ["--module-param", f"{stream_uid}={file_by_uid[file_uid].local_path}"]
            )
        consolidate_command = [
            "gwaith_consolidate_params",
            "--round",
            str(max(workflow_graph.rounds - 1, 0)),
            *module_params,
            "--output",
            str(consolidated_output),
        ]
        _write_executable(
            consolidate_path, _script_header() + _render_command(consolidate_command)
        )
        scripts["consolidate"] = str(consolidate_path)

        final_noise_file_uid = workflow_graph.final_noise_file
        if final_noise_file_uid is not None:
            final_noise_path = scripts_dir / "finalize_noise_estimate.sh"
            residual_file = file_by_uid[workflow_graph.final_residual_file]
            noise_file = file_by_uid[final_noise_file_uid]
            final_noise_output = final_dir / Path(noise_file.local_path).name
            final_noise_command = [
                "gwaith_estimate_psd",
                "--data",
                residual_file.local_path,
                "--data-dataset",
                residual_file.dataset or _DEFAULT_DATASET,
                "--output",
                str(final_noise_output),
                "--output-dataset",
                noise_file.dataset or _DEFAULT_PSD_DATASET,
            ]
            _write_executable(
                final_noise_path,
                _script_header() + _render_command(final_noise_command),
            )
            scripts["final_noise"] = str(final_noise_path)

        return scripts

    def _write_master_script(
        self,
        workflow_graph: GwaithWorkflow,
        workflow_dir: Path,
        node_scripts: dict[str, str],
        finalize_scripts: dict[str, str],
    ) -> str:
        state_file_path = workflow_dir / "job_state.tsv"
        max_retries = 3

        with open(state_file_path, "w", encoding="utf-8") as state_f:
            for entry in workflow_graph.round_entries:
                for node_uid in entry["fit_nodes"]:
                    rel_path = Path(node_scripts[node_uid]).relative_to(workflow_dir)
                    state_f.write(f"{node_uid}\tRETRY\t{max_retries}\t{rel_path}\n")
                for node_uid in entry["prep_nodes"]:
                    rel_path = Path(node_scripts[node_uid]).relative_to(workflow_dir)
                    state_f.write(f"{node_uid}\tRETRY\t{max_retries}\t{rel_path}\n")
                node_uid = entry["combined_residual_node"]
                rel_path = Path(node_scripts[node_uid]).relative_to(workflow_dir)
                state_f.write(f"{node_uid}\tRETRY\t{max_retries}\t{rel_path}\n")
                if entry["noise_node"]:
                    node_uid = entry["noise_node"]
                    rel_path = Path(node_scripts[node_uid]).relative_to(workflow_dir)
                    state_f.write(f"{node_uid}\tRETRY\t{max_retries}\t{rel_path}\n")

            rel_path = Path(finalize_scripts["consolidate"]).relative_to(workflow_dir)
            state_f.write(f"finalize_consolidate\tRETRY\t{max_retries}\t{rel_path}\n")
            if "final_noise" in finalize_scripts:
                rel_path = Path(finalize_scripts["final_noise"]).relative_to(
                    workflow_dir
                )
                state_f.write(f"finalize_noise\tRETRY\t{max_retries}\t{rel_path}\n")

        master_path = workflow_dir / "run_workflow.sh"
        _write_executable(master_path, _CONTROLLER_SCRIPT)
        return str(master_path)

    def _write_manifest(
        self,
        workflow_graph: GwaithWorkflow,
        workflow_dir: Path,
        node_scripts: dict[str, str],
        finalize_scripts: dict[str, str],
        master_script: str,
    ) -> str:
        file_by_uid = _file_lookup(workflow_graph)
        node_by_uid = _node_lookup(workflow_graph)
        stream_by_uid = {stream.uid: stream for stream in workflow_graph.streams}
        manifest = {
            "workflow": {
                "name": workflow_graph.name,
                "workflow_dir": str(workflow_dir),
                "rounds": workflow_graph.rounds,
            },
            "input": workflow_graph.input,
            "streams": {
                uid: _serialise_stream(stream) for uid, stream in stream_by_uid.items()
            },
            "nodes": {
                uid: {
                    **_serialise_node(node),
                    "script": node_scripts.get(uid),
                }
                for uid, node in node_by_uid.items()
            },
            "files": {
                uid: _serialise_file(gwaith_file)
                for uid, gwaith_file in file_by_uid.items()
            },
            "round_entries": workflow_graph.round_entries,
            "final": {
                "residual_file": workflow_graph.final_residual_file,
                "noise_file": workflow_graph.final_noise_file,
                "params": workflow_graph.final_params,
                "scripts": finalize_scripts,
            },
            "master_script": master_script,
        }
        manifest_path = workflow_dir / "workflow_manifest.yaml"
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        return str(manifest_path)