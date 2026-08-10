"""Helper functions for GWAITH workflow graph construction."""

from __future__ import annotations

import re

_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")


def _safe_token(value: str) -> str:
    token = _NON_ALNUM_RE.sub("_", str(value)).strip("_")
    return token or "item"


def make_node_uid(
    stream_uid: str,
    round_index: int | None,
    kind: str = "node",
) -> str:
    round_token = "final" if round_index is None else f"r{int(round_index):03d}"
    return f"node_{_safe_token(stream_uid)}_{round_token}_{_safe_token(kind)}"


def make_file_uid(
    stream_uid: str,
    round_index: int | None,
    kind: str = "file",
) -> str:
    round_token = "final" if round_index is None else f"r{int(round_index):03d}"
    return f"file_{_safe_token(stream_uid)}_{round_token}_{_safe_token(kind)}"


def register_file(files: dict, gwaith_file) -> None:
    if gwaith_file.uid in files:
        raise ValueError(f"Duplicate file UID: {gwaith_file.uid}")
    files[gwaith_file.uid] = gwaith_file


def register_node(nodes: dict, files: dict, gwaith_node) -> None:
    if gwaith_node.uid in nodes:
        raise ValueError(f"Duplicate node UID: {gwaith_node.uid}")
    nodes[gwaith_node.uid] = gwaith_node
    for file_uid in gwaith_node.uses:
        if file_uid not in files:
            raise KeyError(f"Node {gwaith_node.uid} uses unknown file {file_uid}")
        files[file_uid].used_by.append(gwaith_node.uid)
