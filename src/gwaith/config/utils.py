import logging
import re
from functools import reduce

logger = logging.getLogger("gwaith.config.utils")


def safe_update(original, updates, path=None):
    if path is None:
        path = []

    for key, value in updates.items():
        # Build the current path for error reporting
        current_path = path + [str(key)]
        formatted_path = "".join(f"[{k}]" for k in current_path)

        if key in original:
            # Check if we should dive deeper
            if isinstance(original[key], dict) and isinstance(value, dict):
                safe_update(original[key], value, current_path)
            else:
                # Conflict found: report the full breadcrumb path
                raise ValueError(f"Conflict detected in {formatted_path}")
        else:
            # No conflict, safe to add/update
            original[key] = value

    return original


def get_dict_value(data_dict, path_list):
    current_path = []
    try:

        def traverse(d, key):
            current_path.append(key)
            return d[key]

        return reduce(traverse, path_list, data_dict)
    except (KeyError, TypeError):
        path_str = "".join(f"[{k}]" for k in current_path)
        raise LookupError(f"Path does not exist: {path_str}")


_TOKEN_RE = re.compile(r"\$\{([^}]+)\}")


def resolve_match(string_to_match, full_dict, path=None):
    if path is None:
        path = []

    # If it's not a string at all, we can't interpolate - raise an error
    if not isinstance(string_to_match, str):
        logger.error("Could not work out how to interpolate %s", string_to_match)

    if not re.search(_TOKEN_RE, string_to_match):
        logger.debug("No interpolation required for: [%s]", "][".join(path))
        return string_to_match

    def replace_token(match):
        # match.group(1) is the content inside ${...}
        content = match.group(1).strip()

        if "|" not in content:
            # Local lookup: same section as current key
            path_to_resolve_to = path[:-1] + [content]
        else:
            # Global lookup: absolute path
            path_to_resolve_to = content.split("|")

        # Get the value (recursive call to handle nested interpolations)
        resolved_value = get_dict_value(full_dict, path_to_resolve_to)

        # Ensure the resolved value is passed back through interpolation
        # in case the result itself contains tokens
        return str(resolve_match(resolved_value, full_dict, path=path_to_resolve_to))

    # re.sub finds every ${...} and replaces it with the output of replace_token
    interpolated_result = re.sub(_TOKEN_RE, replace_token, string_to_match)

    return interpolated_result


def interpolate_list(l, full_dict, path=None):
    if path is None:
        path = []
    for i, v in enumerate(l):
        current_path = path + [str(i)]
        logger.debug(
            "Interpolating values from list [%s], value %d", "][".join(path), i
        )
        if isinstance(v, dict):
            interpolate_dict(v, full_dict, path=current_path)
        if isinstance(v, list):
            interpolate_list(v, full_dict, path=current_path)
        elif isinstance(v, str):
            l[i] = resolve_match(v, full_dict, path=current_path)
        else:
            logger.error(f"Unknown how to handle value {v}, type {type(v)}")
    return l


def interpolate_dict(d, full_dict=None, path=None):
    if path is None:
        path = []
    if full_dict is None:
        full_dict = d
    logger.debug("Interpolating values in [%s]", "][".join(path))
    for k, v in list(d.items()):
        current_path = path + [str(k)]
        logger.debug("Interpolating values in [%s]", "][".join(current_path))
        if isinstance(v, dict):
            interpolate_dict(v, full_dict, path=current_path)
        elif isinstance(v, list):
            d[k] = interpolate_list(v, full_dict, path=current_path)
        else:
            d[k] = resolve_match(v, full_dict, path=current_path)


__all__ = [
    "get_dict_value",
    "interpolate_dict",
    "interpolate_list",
    "resolve_match",
    "safe_update",
]
