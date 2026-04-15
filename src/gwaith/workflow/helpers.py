from pathlib import Path
from .types import GwaithFile, GwaithNode


def make_node_uid(round_index=None, stream_uid=None):
    parts = ['node']
    if stream_uid is not None:
        parts.append(stream_uid)
    if round_index is not None:
        parts.append(f'{round_index:03d}')
    return '_'.join(parts)


def make_file_uid(round_index=None, stream_uid=None, suffix=None):
    parts = ['file']
    if stream_uid is not None:
        parts.append(stream_uid)
    if round_index is not None:
        parts.append(f'{round_index:03d}')
    if suffix is not None:
        parts.append(suffix)
    return '_'.join(parts)


def register_file(files, file_uid, path, workflow_dir, produced_by=None):
    path_obj = Path(path).expanduser().resolve()
    try:
        final_path = str(path_obj.relative_to(workflow_dir))
    except ValueError:
        final_path = str(path_obj)
    file_obj = GwaithFile(file_uid, path_obj, final_path, produced_by)
    files[file_uid] = file_obj
    return file_obj


def register_node(nodes, node_uid, command, environment, round_index=None, name=None):
    node_obj = GwaithNode(node_uid, command, environment, round_index, name)
    nodes.append(node_obj)
    return node_obj
