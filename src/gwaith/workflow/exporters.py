"""Exporter implementations for universal workflow generation.

This module uses a Template Method style base class to share exporter flow
while allowing backend-specific renderers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from math import gcd
from pathlib import Path
import re
import shlex
from typing import Any
import yaml

from .types import GwaithFile, GwaithNode, GwaithStream


# class SlurmExporter(WorkflowExporter):
#     """Generate one Slurm shell script per node with #SBATCH headers."""

#     def render_artifacts(self, workflow, output_dir):
#         """Render Slurm node scripts and staged runner.

#         Args:
#             workflow (WorkflowDefinition): Workflow definition to render.
#             output_dir (pathlib.Path): Target output directory.

#         Returns:
#             dict[str, str]: Slurm artifact mapping.
#         """
#         artifacts: dict[str, str] = {}
#         for ref in workflow.active_node_refs():
#             cpus = int(ref.node.resources.get('cpus', 1))
#             memory = str(ref.node.resources.get('memory', '2G'))
#             walltime = str(ref.node.resources.get('walltime', '00:30:00'))
#             dependencies = workflow.dependencies_for(ref)
#             header = ['#!/usr/bin/env bash', f'#SBATCH --job-name={workflow.name}_{ref.safe_id}', f'#SBATCH --cpus-per-task={cpus}', f'#SBATCH --mem={memory}', f'#SBATCH --time={walltime}', f'#SBATCH --output={ref.safe_id}.out', 'set -euo pipefail', '', f'# stream: {ref.stream_name}', f'# node: {ref.node.name}', f'# round: {ref.round_index}', f'# output_kind: {workflow.stream_named(ref.stream_name).output_kind}']
#             if dependencies:
#                 header.append(f"# depends_on: {', '.join(dependencies)}")
#                 header.append('')
#             header.extend(workflow.command_lines_for(ref, output_dir))
#             header.append('')
#             artifacts[f'slurm/round_{ref.round_index:03d}/{ref.safe_id}.sh'] = '\n'.join(header)
#         artifacts['run_workflow.sh'] = self._build_runner_script(workflow)
#         return artifacts

#     def _build_runner_script(self, workflow):
#         """Build fail-fast/restartable Slurm workflow runner script.

#         Args:
#             workflow (WorkflowDefinition): Workflow definition.

#         Returns:
#             str: Bash script text.
#         """
#         lines: list[str] = ['#!/usr/bin/env bash', 'set -euo pipefail', '', 'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"', 'CACHE_FILE="${SCRIPT_DIR}/.reuse_cache.txt"', 'touch "${CACHE_FILE}"', '', 'cache_has() {', '  local key="$1"', '  grep -Fxq "${key}" "${CACHE_FILE}"', '}', '', 'cache_add() {', '  local key="$1"', '  if ! cache_has "${key}"; then', '    echo "${key}" >> "${CACHE_FILE}"', '  fi', '}', '', 'prune_rounds() {', '  local current_round="$1"', f'  local keep_decimation={int(workflow.store_decimation or 1)}', '  if (( keep_decimation <= 0 )); then', '    return', '  fi']
#         for stream in workflow.streams:
#             lines.extend([f'  if [[ -d "${{SCRIPT_DIR}}/{stream.name}" ]]; then', f"""    find "${{SCRIPT_DIR}}/{stream.name}" -mindepth 1 -maxdepth 1 -type d -name 'round_*' | while read -r d; do""", '      bn="$(basename "${d}")"', '      rn="${bn#round_}"', '      rn=$((10#${rn}))', '      if (( rn < current_round && rn % keep_decimation != 0 )); then', '        rm -rf "${d}"', '      fi', '    done', '  fi'])
#         lines.extend(['}', ''])
#         for ref in workflow.active_node_refs():
#             node_id = ref.node_id
#             script_rel = f'slurm/round_{ref.round_index:03d}/{ref.safe_id}.sh'
#             lines.append(f'# {node_id}')
#             lines.append(f'if cache_has {shlex.quote(node_id)}; then')
#             lines.append(f'  echo "[reuse] {node_id}"')
#             lines.append('else')
#             for dep in workflow.dependencies_for(ref):
#                 lines.append(f'  if ! cache_has {shlex.quote(dep)}; then')
#                 lines.append(f'    echo "[fail] dependency not satisfied for {node_id}: {dep}" >&2')
#                 lines.append('    exit 1')
#                 lines.append('  fi')
#             lines.append(f'  echo "[run] {node_id}"')
#             lines.append(f'  bash "${{SCRIPT_DIR}}/{script_rel}"')
#             lines.append(f'  cache_add {shlex.quote(node_id)}')
#             lines.append(f'  prune_rounds {ref.round_index}')
#             lines.append('fi')
#             lines.append('')
#         lines.append('echo "[done] workflow complete"')
#         return '\n'.join(lines) + '\n'

# class SnakemakeExporter(WorkflowExporter):
#     """Generate a Snakefile representing stream/node dependencies."""

#     def render_artifacts(self, workflow, output_dir):
#         """Render a Snakemake workflow file.

#         Args:
#             workflow (WorkflowDefinition): Workflow definition to render.
#             output_dir (pathlib.Path): Target output directory.

#         Returns:
#             dict[str, str]: Artifact mapping containing Snakefile content.
#         """
#         lines: list[str] = ['# Auto-generated Snakefile', '']
#         node_refs = [ref for ref in workflow.iter_node_refs() if workflow.should_run(ref)]
#         final_targets = [f'"done/{ref.safe_id}.done"' for ref in node_refs]
#         lines.extend(['rule all:', '    input:', f"        {', '.join(final_targets)}", ''])
#         for ref in node_refs:
#             dependencies = workflow.dependencies_for(ref)
#             inputs = [f'"done/{_safe_name(dep)}.done"' for dep in dependencies]
#             if not inputs:
#                 inputs = ['""']
#             shell_command = ' && '.join(workflow.command_lines_for(ref, output_dir))
#             lines.extend([f'# stream={ref.stream_name} node={ref.node.name} round={ref.round_index}', f'rule {ref.safe_id}:', '    input:', '        ' + ', '.join(inputs), '    output:', f'        "done/{ref.safe_id}.done"', '    shell:', f'        "{shell_command} && mkdir -p done && touch done/{ref.safe_id}.done"', ''])
#         return {'Snakefile': '\n'.join(lines)}

# class HTCondorExporter(WorkflowExporter):
#     """Generate one HTCondor submit file per node."""

#     def render_artifacts(self, workflow, output_dir):
#         """Render HTCondor submit files for active nodes.

#         Args:
#             workflow (WorkflowDefinition): Workflow definition to render.
#             output_dir (pathlib.Path): Target output directory.

#         Returns:
#             dict[str, str]: HTCondor artifact mapping.
#         """
#         artifacts: dict[str, str] = {}
#         for ref in workflow.iter_node_refs():
#             if not workflow.should_run(ref):
#                 continue
#             cpus = int(ref.node.resources.get('cpus', 1))
#             memory = str(ref.node.resources.get('memory_mb', 2048))
#             dependencies = workflow.dependencies_for(ref)
#             shell_command = ' && '.join(workflow.command_lines_for(ref, output_dir))
#             lines = ['universe = vanilla', 'executable = /bin/bash', f'arguments = -lc "{shell_command}"', f'request_cpus = {cpus}', f'request_memory = {memory}', f'output = logs/{ref.safe_id}.out', f'error = logs/{ref.safe_id}.err', f'log = logs/{ref.safe_id}.log', 'queue', '']
#             lines.insert(0, f'# stream: {ref.stream_name}  node: {ref.node.name}  round: {ref.round_index}')
#             if dependencies:
#                 lines.insert(1, f"# depends_on: {', '.join(dependencies)}")
#             artifacts[f'htcondor/round_{ref.round_index:03d}/{ref.safe_id}.sub'] = '\n'.join(lines)
#         return artifacts

# def _safe_name(value):
#     """Sanitize a value for use as a file-safe identifier.

#     Args:
#         value (str): Raw identifier text.

#     Returns:
#         str: Sanitized identifier.
#     """
#     return re.sub('[^A-Za-z0-9_]+', '_', value)

# def _expand_node_template(template, rounds):
#     """Expand a per-round node template into explicit node mappings.

#     Args:
#         template (Any): node_template mapping from config.
#         rounds (int): Highest round index to generate.

#     Returns:
#         list[dict[str, Any]]: Expanded node mappings.
#     """
#     if not isinstance(template, dict):
#         raise ValueError('node_template must be a mapping')
#     base_name = str(template.get('name', 'node'))
#     base_executable = template.get('executable')
#     if base_executable is None:
#         raise ValueError("node_template must define 'executable'")
#     depends_on = template.get('depends_on', [])
#     if not isinstance(depends_on, list):
#         raise ValueError('node_template.depends_on must be a list')
#     input_streams = template.get('input_streams', [])
#     if not isinstance(input_streams, list):
#         raise ValueError('node_template.input_streams must be a list')
#     stream_inputs = template.get('stream_inputs', {})
#     if not isinstance(stream_inputs, dict):
#         raise ValueError('node_template.stream_inputs must be a mapping')
#     options = template.get('options', {})
#     if not isinstance(options, dict):
#         raise ValueError('node_template.options must be a mapping')
#     resources = template.get('resources', {})
#     if not isinstance(resources, dict):
#         raise ValueError('node_template.resources must be a mapping')
#     nodes: list[dict[str, Any]] = []
#     for round_idx in range(rounds + 1):
#         nodes.append({'name': f'{base_name}_r{round_idx:03d}', 'round': round_idx, 'executable': str(base_executable), 'options': _format_template_mapping(options, round_idx), 'depends_on': list(depends_on), 'input_streams': list(input_streams), 'stream_inputs': dict(stream_inputs), 'resources': dict(resources)})
#     return nodes

# def _format_template_mapping(mapping, round_idx):
#     """Recursively format template values within a mapping.

#     Args:
#         mapping (dict[str, Any]): Mapping with template values.
#         round_idx (int): Round index used for formatting context.

#     Returns:
#         dict[str, Any]: Mapping with formatted values.
#     """
#     return {key: _format_template_value(value, round_idx) for key, value in mapping.items()}

# def _format_template_value(value, round_idx):
#     """Recursively apply round-based formatting to template values.

#     Args:
#         value (Any): Template-compatible value.
#         round_idx (int): Round index used for formatting.

#     Returns:
#         Any: Formatted value.
#     """
#     if isinstance(value, str):
#         return value.format(round=round_idx, prev_round=max(0, round_idx - 1))
#     if isinstance(value, list):
#         return [_format_template_value(item, round_idx) for item in value]
#     if isinstance(value, dict):
#         return {key: _format_template_value(item, round_idx) for key, item in value.items()}
#     return value

# def _resolve_stream_parameters(raw_params):
#     """Resolve cross-stream parameter interpolation tokens.

#     Args:
#         raw_params (dict[str, dict[str, Any]]): Raw stream parameter mapping.

#     Returns:
#         dict[str, dict[str, Any]]: Resolved stream parameter mapping.
#     """
#     token_re = re.compile('\\$\\{([^}]+)\\}')
#     resolved: dict[str, dict[str, Any]] = {stream_name: {} for stream_name in raw_params}

#     def resolve_value(stream_name, param_name, stack):
#         """Resolve one stream parameter value recursively.

#         Args:
#             stream_name (str): Source stream name.
#             param_name (str): Parameter name in source stream.
#             stack (list[tuple[str, str]]): Resolution stack for cycle detection.

#         Returns:
#             Any: Resolved parameter value.
#         """
#         if param_name in resolved.get(stream_name, {}):
#             return resolved[stream_name][param_name]
#         stream_params = raw_params.get(stream_name, {})
#         if param_name not in stream_params:
#             raise KeyError(f'Missing stream parameter reference: {stream_name}.{param_name}')
#         value = stream_params[param_name]
#         if not isinstance(value, str):
#             return value

#         def replacement(match):
#             """Replace a token with its resolved parameter value.

#             Args:
#                 match (re.Match): Token match object.

#             Returns:
#                 str: Replacement text.
#             """
#             token = match.group(1).strip()
#             if '|' in token:
#                 target_stream, target_param = token.split('|', 1)
#             elif ':' in token:
#                 target_stream, target_param = token.split(':', 1)
#             else:
#                 target_stream = stream_name
#                 target_param = token
#             key = (target_stream.strip(), target_param.strip())
#             if key in stack:
#                 cycle = ' -> '.join((f'{s}.{p}' for s, p in [*stack, key]))
#                 raise ValueError(f'Stream parameter interpolation cycle detected: {cycle}')
#             return str(resolve_value(key[0], key[1], [*stack, key]))
#         return token_re.sub(replacement, value)
#     for stream_name, params in raw_params.items():
#         for param_name in params:
#             resolved[stream_name][param_name] = resolve_value(stream_name, param_name, [(stream_name, param_name)])
#     return resolved

# def _load_yaml_mapping(path):
#     """Load a YAML file expected to contain a mapping.

#     Args:
#         path (pathlib.Path): YAML file path.

#     Returns:
#         dict[str, Any]: Parsed mapping.
#     """
#     with path.open('r', encoding='utf-8') as f:
#         data = yaml.safe_load(f) or {}
#     if not isinstance(data, dict):
#         raise ValueError(f'YAML file must parse to a mapping: {path}')
#     return data

# def _lcm(a, b):
#     """Compute least common multiple for two integers.

#     Args:
#         a (int): First integer.
#         b (int): Second integer.

#     Returns:
#         int: Least common multiple.
#     """
#     if a == 0 or b == 0:
#         return 0
#     return abs(a * b) // gcd(a, b)

# def _lcm_list(values):
#     """Compute least common multiple for an integer list.

#     Args:
#         values (list[int]): Integer values.

#     Returns:
#         int: Least common multiple (minimum 1).
#     """
#     result = 1
#     for value in values:
#         result = _lcm(result, int(value))
#     return max(1, result)
