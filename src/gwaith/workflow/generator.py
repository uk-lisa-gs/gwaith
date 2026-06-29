"""Workflow graph construction and output generation."""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import yaml

from .helpers import make_file_uid, make_node_uid, register_file, register_node
from .types import GwaithFile, GwaithNode, GwaithStream, GwaithWorkflow


_GLOBAL_SECTIONS = {"workflow", "executables", "default_resources"}
_INFRA_SECTIONS = {"processor", "subtraction", "noise"}
_ROUND_TAG_TEMPLATE = "round_{round_index:03d}"
_DEFAULT_DATASET = "data"
_DEFAULT_SIGNAL_DATASET = "signal"
_DEFAULT_PSD_DATASET = "psd"


def _safe_name(value: str) -> str:
	return re.sub(r"[^A-Za-z0-9]+", "_", str(value)).strip("_") or "item"


def _round_tag(round_index: int) -> str:
	return _ROUND_TAG_TEMPLATE.format(round_index=int(round_index))


def _as_path(value: str | Path) -> str:
	return str(Path(value).expanduser())


def _script_header() -> str:
	return "#!/usr/bin/env bash\nset -euo pipefail\n\n"


def _write_executable(path: Path, content: str) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(content, encoding="utf-8")
	path.chmod(path.stat().st_mode | 0o111)


def _render_command(command: list[str]) -> str:
	return shlex.join([str(part) for part in command]) + "\n"


def _normalise_stream_decimation(stream_cfg: dict[str, Any]) -> int:
	value = stream_cfg.get("stream_decimation", stream_cfg.get("stream-decimation", 1))
	decimation = int(value)
	if decimation < 1:
		raise ValueError("stream_decimation must be >= 1")
	return decimation


def _normalise_stream_offset(stream_cfg: dict[str, Any]) -> int:
	return int(
		stream_cfg.get(
			"stream_decimation_offset",
			stream_cfg.get("stream-decimation-offset", 0),
		)
	)


def _normalise_skip_rounds(stream_cfg: dict[str, Any]) -> set[int]:
	raw = stream_cfg.get("skip_rounds", stream_cfg.get("skip-rounds", []))
	if raw is None:
		return set()
	if not isinstance(raw, list):
		raise ValueError("skip_rounds must be a list")
	return {int(value) for value in raw}


def _normalise_stream_outputs(
	stream_cfg: dict[str, Any], options: dict[str, Any]
) -> list[dict[str, Any]]:
	"""Return normalised output artifact definitions for a stream.

	The default output is the standard signal artifact written via
	--output-signal/--output-signal-dataset.
	Additional outputs may be provided under stream output_files/output-files.
	"""
	outputs: list[dict[str, Any]] = [
		{
			"id": "signal",
			"arg": "output-signal",
			"dataset_arg": "output-signal-dataset",
			"dataset": str(options.get("output-signal-dataset", _DEFAULT_SIGNAL_DATASET)),
			"kind": "signal",
			"extension": "hdf",
			"include_in_subtraction": True,
		}
	]

	raw_outputs = stream_cfg.get("output_files", stream_cfg.get("output-files", []))
	if raw_outputs is None:
		raw_outputs = []
	if not isinstance(raw_outputs, list):
		raise ValueError("output_files must be a list")

	for index, raw_output in enumerate(raw_outputs):
		if not isinstance(raw_output, dict):
			raise ValueError("Each output_files entry must be a mapping")

		output_id = _safe_name(raw_output.get("id") or raw_output.get("name") or f"output_{index}")
		if output_id == "signal":
			# The primary signal output is always present and reserved.
			continue

		arg_name = str(raw_output.get("arg") or raw_output.get("output-arg") or f"output-{output_id}")
		arg_name = arg_name.lstrip("-")

		dataset_arg = raw_output.get("dataset_arg", raw_output.get("output-dataset-arg"))
		dataset_value = raw_output.get("dataset")
		kind = str(raw_output.get("kind", "artifact"))
		extension = str(raw_output.get("extension", "hdf")).lstrip(".") or "hdf"
		include_in_subtraction = bool(
			raw_output.get(
				"include_in_subtraction",
				raw_output.get("include-in-subtraction", kind == "signal"),
			)
		)

		outputs.append(
			{
				"id": output_id,
				"arg": arg_name,
				"dataset_arg": str(dataset_arg) if dataset_arg else None,
				"dataset": str(dataset_value) if dataset_value is not None else None,
				"kind": kind,
				"extension": extension,
				"include_in_subtraction": include_in_subtraction,
			}
		)

	return outputs


def _stream_runs_on_round(stream_cfg: dict[str, Any], round_index: int) -> bool:
	if round_index in stream_cfg["skip_rounds"]:
		return False
	return (round_index - stream_cfg["decimation_offset"]) % stream_cfg["decimation"] == 0


def _build_cli_args(options: dict[str, Any], excluded: set[str] | None = None) -> list[str]:
	excluded = excluded or set()
	args: list[str] = []
	for key, value in options.items():
		if key in excluded:
			continue
		flag = f"--{key}"
		if isinstance(value, bool):
			if value:
				args.append(flag)
			continue
		if value == "" or value is None:
			args.append(flag)
			continue
		if isinstance(value, list):
			for item in value:
				args.extend([flag, str(item)])
			continue
		args.extend([flag, str(value)])
	return args


def _serialise_file(gwaith_file: GwaithFile) -> dict[str, Any]:
	return {
		"uid": gwaith_file.uid,
		"path": gwaith_file.path,
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


def _parse_config(config_parser, workflow_name: str | None, workflow_dir: str | None) -> dict[str, Any]:
	data = config_parser.data
	workflow_cfg = data.get("workflow", {})
	if not isinstance(workflow_cfg, dict):
		raise ValueError("workflow section must be a mapping")

	processor_cfg = data.get("processor", {})
	if not isinstance(processor_cfg, dict):
		raise ValueError("processor section must be a mapping")
	processor_options = processor_cfg.get("options", {}) or {}

	input_file = (
		processor_options.get("input-file")
		or processor_options.get("data-file")
		or workflow_cfg.get("input-file")
		or workflow_cfg.get("data-file")
	)
	input_dataset = str(processor_options.get("input-dataset") or _DEFAULT_DATASET)

	executables = data.get("executables", {})
	if not isinstance(executables, dict):
		raise ValueError("executables section must be a mapping")

	rounds = int(workflow_cfg.get("rounds", 1))
	if rounds < 1:
		raise ValueError("workflow.rounds must be >= 1")

	name = str(workflow_name or workflow_cfg.get("name") or "gwaith_workflow")
	target_dir = Path(workflow_dir or workflow_cfg.get("output_dir") or name).expanduser().resolve()

	subtraction_cfg = data.get("subtraction", {}) if isinstance(data.get("subtraction", {}), dict) else {}
	noise_cfg = data.get("noise", {}) if isinstance(data.get("noise", {}), dict) else {}

	signal_streams: list[dict[str, Any]] = []
	for section_name, section_cfg in data.items():
		if section_name in _GLOBAL_SECTIONS or section_name in _INFRA_SECTIONS:
			continue
		if not isinstance(section_cfg, dict):
			continue
		if section_name not in executables:
			continue
		options = dict(section_cfg.get("options", {}) or {})
		signal_streams.append(
			{
				"uid": _safe_name(section_name),
				"section_name": section_name,
				"name": section_name,
				"executable": str(executables[section_name]),
				"decimation": _normalise_stream_decimation(section_cfg),
				"decimation_offset": _normalise_stream_offset(section_cfg),
				"skip_rounds": _normalise_skip_rounds(section_cfg),
				"resources": dict(section_cfg.get("resources", {}) or {}),
				"options": options,
				"outputs": _normalise_stream_outputs(section_cfg, options),
				"initial_prior": options.get("prior-file") or options.get("priors") or options.get("init-params"),
			}
		)

	if not signal_streams:
		raise ValueError("At least one signal stream must be defined in the parsed config")

	return {
		"name": name,
		"workflow_dir": target_dir,
		"rounds": rounds,
		"input_file": _as_path(input_file) if input_file else "data.hdf",
		"input_dataset": input_dataset,
		"global_retention_level": workflow_cfg.get("global-retention-level"),
		"signal_streams": signal_streams,
		"subtraction": {
			"executable": str(executables.get("subtraction", "gwaith_subtract_signals")),
			"options": dict(subtraction_cfg.get("options", {}) or {}),
			"resources": dict(subtraction_cfg.get("resources", {}) or {}),
		},
		"noise": {
			"enabled": "noise" in executables,
			"executable": str(executables.get("noise", "gwaith_estimate_psd")),
			"options": dict(noise_cfg.get("options", {}) or {}),
			"resources": dict(noise_cfg.get("resources", {}) or {}),
		},
	}


def build_workflow_graph(config_parser, workflow_name: str | None = None, workflow_dir: str | None = None) -> GwaithWorkflow:
	cfg = _parse_config(config_parser, workflow_name=workflow_name, workflow_dir=workflow_dir)
	target_dir: Path = cfg["workflow_dir"]

	files: dict[str, GwaithFile] = {}
	nodes: dict[str, GwaithNode] = {}
	streams: dict[str, GwaithStream] = {}

	original_data_uid = make_file_uid("processor", None, "input_data")
	original_data_file = GwaithFile(
		uid=original_data_uid,
		path=cfg["input_file"],
		final_path=cfg["input_file"],
		dataset=cfg["input_dataset"],
		kind="input_data",
		round_index=None,
		stream_uid="processor",
		retention_level=cfg["global_retention_level"],
	)
	register_file(files, original_data_file)

	streams["central"] = GwaithStream(uid="central", environment="bash", name="central")
	if cfg["noise"]["enabled"]:
		streams["noise"] = GwaithStream(uid="noise", environment="bash", name="noise")

	initial_prior_by_stream: dict[str, str | None] = {}
	subtractable_output_uids_by_stream_round: dict[str, dict[int, list[str]]] = {}
	prior_uid_by_stream_round: dict[str, dict[int, str]] = {}
	next_data_by_stream: dict[str, str] = {}

	def _latest_produced_round(stream_uid: str, max_round_inclusive: int) -> int | None:
		"""Find the latest round where the stream produced output (ran on that round)."""
		if max_round_inclusive < 0:
			return None
		stream = streams[stream_uid]
		# Compute the latest round that matches the decimation pattern
		candidate = ((max_round_inclusive - stream.decimation_offset) // stream.decimation) * stream.decimation + stream.decimation_offset
		# Iterate backwards from candidate, checking skip_rounds. This accounts for skipped rounds.
		for round_index in range(candidate, -1, -stream.decimation):
			if round_index in stream.skip_rounds:
				continue
			return round_index
		return None

	for stream_cfg in cfg["signal_streams"]:
		stream_uid = stream_cfg["uid"]
		streams[stream_uid] = GwaithStream(
			uid=stream_uid,
			environment="bash",
			name=stream_cfg["name"],
			decimation=stream_cfg["decimation"],
			decimation_offset=stream_cfg["decimation_offset"],
			skip_rounds=sorted(stream_cfg["skip_rounds"]),
		)
		subtractable_output_uids_by_stream_round[stream_uid] = {}
		prior_uid_by_stream_round[stream_uid] = {}
		next_data_by_stream[stream_uid] = original_data_uid
		initial_prior_by_stream[stream_uid] = None

		initial_prior = stream_cfg.get("initial_prior")
		if initial_prior:
			prior_uid = make_file_uid(stream_uid, None, "initial_prior")
			prior_file = GwaithFile(
				uid=prior_uid,
				path=_as_path(initial_prior),
				final_path=_as_path(initial_prior),
				dataset=None,
				kind="initial_prior",
				round_index=None,
				stream_uid=stream_uid,
				retention_level=cfg["global_retention_level"],
			)
			register_file(files, prior_file)
			initial_prior_by_stream[stream_uid] = prior_uid

	round_entries: list[dict[str, Any]] = []
	latest_params_by_stream: dict[str, str | None] = {
		stream_cfg["uid"]: initial_prior_by_stream[stream_cfg["uid"]]
		for stream_cfg in cfg["signal_streams"]
	}
	final_residual_uid: str = original_data_uid
	final_noise_uid: str | None = None

	for round_index in range(cfg["rounds"]):
		round_tag = _round_tag(round_index)
		round_dir = target_dir / round_tag
		active_fit_nodes: list[str] = []
		prep_nodes: list[str] = []
		active_stream_uids: list[str] = []

		for stream_cfg in cfg["signal_streams"]:
			stream_uid = stream_cfg["uid"]
			if not _stream_runs_on_round(stream_cfg, round_index):
				continue

			active_stream_uids.append(stream_uid)
			fit_node_uid = make_node_uid(stream_uid, round_index, "fit")
			fit_node = GwaithNode(
				uid=fit_node_uid,
				round_index=round_index,
				stream_uid=stream_uid,
				name=f"{stream_uid}_fit_{round_tag}",
				resources=stream_cfg["resources"],
			)

			input_data_uid = next_data_by_stream[stream_uid]
			input_file = files[input_data_uid]
			fit_node.uses.append(input_data_uid)

			latest_prior_round = _latest_produced_round(stream_uid, round_index - 1)
			prior_uid = None
			if latest_prior_round is not None:
				prior_uid = prior_uid_by_stream_round[stream_uid].get(latest_prior_round)
			if prior_uid is None:
				prior_uid = initial_prior_by_stream[stream_uid]
			if prior_uid and prior_uid in files:
				fit_node.uses.append(prior_uid)
			else:
				prior_uid = None

			likelihood_path = str(round_dir / f"{round_tag}_{stream_uid}_likelihood.yaml")
			stream_outputs: list[dict[str, Any]] = stream_cfg["outputs"]
			output_paths: dict[str, str] = {}
			for output_cfg in stream_outputs:
				output_paths[output_cfg["id"]] = str(
					round_dir / f"{round_tag}_{stream_uid}_{output_cfg['id']}.{output_cfg['extension']}"
				)

			command = [
				stream_cfg["executable"],
				"--data",
				input_file.path,
				"--data-dataset",
				input_file.dataset or _DEFAULT_DATASET,
			]
			if prior_uid:
				command.extend(["--priors", files[prior_uid].path])
			command.extend(
				_build_cli_args(
					stream_cfg["options"],
					excluded={"prior-file", "priors", "init-params", "output-signal-dataset"},
				)
			)
			for output_cfg in stream_outputs:
				output_arg = f"--{output_cfg['arg']}"
				output_path = output_paths[output_cfg["id"]]
				command.extend([output_arg, output_path])
				dataset_arg = output_cfg.get("dataset_arg")
				dataset_value = output_cfg.get("dataset")
				if dataset_arg and dataset_value:
					command.extend([f"--{dataset_arg}", dataset_value])
			command.extend(["--output-params", likelihood_path])
			fit_node.command = command

			likelihood_uid = make_file_uid(stream_uid, round_index, "likelihood")
			produced_output_uids: list[str] = []
			subtractable_output_uids: list[str] = []
			for output_cfg in stream_outputs:
				output_id = output_cfg["id"]
				output_uid = make_file_uid(stream_uid, round_index, output_id)
				output_path = output_paths[output_id]
				output_file = GwaithFile(
					uid=output_uid,
					path=output_path,
					final_path=output_path,
					produced_by=fit_node_uid,
					retention_level=cfg["global_retention_level"],
					dataset=output_cfg.get("dataset"),
					kind=output_cfg.get("kind", "artifact"),
					round_index=round_index,
					stream_uid=stream_uid,
				)
				register_file(files, output_file)
				produced_output_uids.append(output_uid)
				if output_cfg.get("include_in_subtraction", False):
					subtractable_output_uids.append(output_uid)

			likelihood_file = GwaithFile(
				uid=likelihood_uid,
				path=likelihood_path,
				final_path=likelihood_path,
				produced_by=fit_node_uid,
				retention_level=cfg["global_retention_level"],
				dataset=None,
				kind="likelihood",
				round_index=round_index,
				stream_uid=stream_uid,
			)
			register_file(files, likelihood_file)
			fit_node.produces.extend(produced_output_uids)
			fit_node.produces.append(likelihood_uid)
			register_node(nodes, files, fit_node)
			streams[stream_uid].nodes.append(fit_node_uid)
			active_fit_nodes.append(fit_node_uid)

			subtractable_output_uids_by_stream_round[stream_uid][round_index] = subtractable_output_uids
			prior_uid_by_stream_round[stream_uid][round_index] = likelihood_uid
			latest_params_by_stream[stream_uid] = likelihood_uid

		residual_uid = make_file_uid("central", round_index, "combined_residual")
		residual_path = str(round_dir / f"{round_tag}_combined_residual.hdf")
		residual_node_uid = make_node_uid("central", round_index, "combined_residual")
		residual_node = GwaithNode(
			uid=residual_node_uid,
			round_index=round_index,
			stream_uid="central",
			name=f"combined_residual_{round_tag}",
			resources=cfg["subtraction"]["resources"],
		)
		residual_signal_uids: list[str] = []
		for stream_cfg in cfg["signal_streams"]:
			stream_uid = stream_cfg["uid"]
			latest_signal_round = _latest_produced_round(stream_uid, round_index)
			if latest_signal_round is None:
				continue
			for signal_uid in subtractable_output_uids_by_stream_round[stream_uid].get(latest_signal_round, []):
				if signal_uid in files:
					residual_signal_uids.append(signal_uid)
		residual_node.uses.append(original_data_uid)
		residual_node.uses.extend(residual_signal_uids)
		if residual_signal_uids:
			residual_command = [
				cfg["subtraction"]["executable"],
				"--data",
				files[original_data_uid].path,
				"--data-dataset",
				files[original_data_uid].dataset or _DEFAULT_DATASET,
			]
			for signal_uid in residual_signal_uids:
				residual_command.extend(["--signal", files[signal_uid].path])
			for signal_uid in residual_signal_uids:
				residual_command.extend(["--signal-dataset", files[signal_uid].dataset or _DEFAULT_SIGNAL_DATASET])
			residual_command.extend(
				_build_cli_args(cfg["subtraction"]["options"])
			)
			residual_command.extend(["--output", residual_path, "--output-dataset", _DEFAULT_DATASET])
		else:
			residual_command = ["cp", files[original_data_uid].path, residual_path]
		residual_node.command = residual_command
		residual_file = GwaithFile(
			uid=residual_uid,
			path=residual_path,
			final_path=residual_path,
			produced_by=residual_node_uid,
			retention_level=cfg["global_retention_level"],
			dataset=_DEFAULT_DATASET,
			kind="combined_residual",
			round_index=round_index,
			stream_uid="central",
		)
		register_file(files, residual_file)
		residual_node.produces.append(residual_uid)
		register_node(nodes, files, residual_node)
		streams["central"].nodes.append(residual_node_uid)
		final_residual_uid = residual_uid

		noise_node_uid: str | None = None
		if cfg["noise"]["enabled"]:
			noise_uid = make_file_uid("noise", round_index, "psd")
			noise_path = str(round_dir / f"{round_tag}_noise.hdf")
			noise_node_uid = make_node_uid("noise", round_index, "estimate_psd")
			noise_node = GwaithNode(
				uid=noise_node_uid,
				round_index=round_index,
				stream_uid="noise",
				name=f"noise_{round_tag}",
				resources=cfg["noise"]["resources"],
			)
			noise_node.uses.append(residual_uid)
			noise_node.command = [
				cfg["noise"]["executable"],
				"--data",
				residual_path,
				"--data-dataset",
				_DEFAULT_DATASET,
			]
			noise_node.command.extend(_build_cli_args(cfg["noise"]["options"]))
			noise_node.command.extend(["--output", noise_path, "--output-dataset", _DEFAULT_PSD_DATASET])

			noise_file = GwaithFile(
				uid=noise_uid,
				path=noise_path,
				final_path=noise_path,
				produced_by=noise_node_uid,
				retention_level=cfg["global_retention_level"],
				dataset=_DEFAULT_PSD_DATASET,
				kind="psd",
				round_index=round_index,
				stream_uid="noise",
			)
			register_file(files, noise_file)
			noise_node.produces.append(noise_uid)
			register_node(nodes, files, noise_node)
			streams["noise"].nodes.append(noise_node_uid)
			final_noise_uid = noise_uid

		if round_index + 1 < cfg["rounds"]:
			next_round_dir = target_dir / _round_tag(round_index + 1)
			for stream_cfg in cfg["signal_streams"]:
				stream_uid = stream_cfg["uid"]
				prep_node_uid = make_node_uid("central", round_index, f"prep_{stream_uid}")
				prep_node = GwaithNode(
					uid=prep_node_uid,
					round_index=round_index,
					stream_uid="central",
					name=f"prepare_{stream_uid}_input_{round_tag}",
					resources=cfg["subtraction"]["resources"],
				)
				prep_node.uses.append(original_data_uid)
				other_signal_uids: list[str] = []
				for other_stream_cfg in cfg["signal_streams"]:
					other_stream_uid = other_stream_cfg["uid"]
					if other_stream_uid == stream_uid:
						continue
					latest_signal_round = _latest_produced_round(other_stream_uid, round_index)
					if latest_signal_round is None:
						continue
					for signal_uid in subtractable_output_uids_by_stream_round[other_stream_uid].get(latest_signal_round, []):
						if signal_uid in files:
							other_signal_uids.append(signal_uid)
				prep_node.uses.extend(other_signal_uids)

				next_data_uid = make_file_uid(stream_uid, round_index + 1, "input_data")
				next_data_path = str(next_round_dir / f"{_round_tag(round_index + 1)}_{stream_uid}_input_data.hdf")
				if other_signal_uids:
					prep_command = [
						cfg["subtraction"]["executable"],
						"--data",
						files[original_data_uid].path,
						"--data-dataset",
						files[original_data_uid].dataset or _DEFAULT_DATASET,
					]
					for signal_uid in other_signal_uids:
						prep_command.extend(["--signal", files[signal_uid].path])
					for signal_uid in other_signal_uids:
						prep_command.extend(["--signal-dataset", files[signal_uid].dataset or _DEFAULT_SIGNAL_DATASET])
					prep_command.extend(_build_cli_args(cfg["subtraction"]["options"]))
					prep_command.extend(["--output", next_data_path, "--output-dataset", _DEFAULT_DATASET])
				else:
					prep_command = ["cp", files[original_data_uid].path, next_data_path]
				prep_node.command = prep_command

				next_data_file = GwaithFile(
					uid=next_data_uid,
					path=next_data_path,
					final_path=next_data_path,
					produced_by=prep_node_uid,
					retention_level=cfg["global_retention_level"],
					dataset=_DEFAULT_DATASET,
					kind="input_data",
					round_index=round_index + 1,
					stream_uid=stream_uid,
				)
				register_file(files, next_data_file)
				prep_node.produces.append(next_data_uid)
				register_node(nodes, files, prep_node)
				streams["central"].nodes.append(prep_node_uid)
				prep_nodes.append(prep_node_uid)
				next_data_by_stream[stream_uid] = next_data_uid

		round_entries.append(
			{
				"round": round_index,
				"active_streams": active_stream_uids,
				"fit_nodes": active_fit_nodes,
				"prep_nodes": prep_nodes,
				"combined_residual_node": residual_node_uid,
				"combined_residual_file": residual_uid,
				"noise_node": noise_node_uid,
			}
		)

	workflow = GwaithWorkflow(
		cp=config_parser,
		name=cfg["name"],
		workflow_dir=str(target_dir),
		rounds=cfg["rounds"],
		input_data={
			"data_file": cfg["input_file"],
			"data_dataset": cfg["input_dataset"],
		},
		global_retention_level=cfg["global_retention_level"],
	)
	workflow.streams = list(streams.values())
	workflow.nodes = list(nodes.values())
	workflow.files = list(files.values())
	workflow.round_entries = round_entries
	workflow.final_residual_file = final_residual_uid
	workflow.final_noise_file = final_noise_uid
	workflow.final_params = latest_params_by_stream
	return workflow



def build_workflow(
		config_parser, 
		workflow_name: str | None = None,
		workflow_dir: str | None = None,
) -> GwaithWorkflow:
	"""Build a workflow graph.
	
	Args:
		config_parser: Configuration parser with workflow settings
		workflow_name: Optional name for the workflow
		workflow_dir: Optional output directory for the workflow
		
	Returns:
		GwaithWorkflow
	"""
	workflow_graph = build_workflow_graph(
		config_parser,
		workflow_name=workflow_name,
		workflow_dir=workflow_dir,
	)
	return workflow_graph
