import re
from pathlib import Path
from typing import Any

_TOKEN_RE = re.compile("\\$\\{([^}]+)\\}")


class GwaithConfig(dict):
    """A dictionary-like object for handling GWAITH configuration."""

    def __init__(self, parser):
        self._data = None
        self._parser = parser

    def write(self, filepath: str | Path) -> None:
        """Write a configuration file, auto-detecting format from extension.

        Parameters
        ----------
        filepath:
            Path to the configuration file.

        Raises
        ------
        ValueError:
            If file extension is not recognized.
        """
        suffix = Path(filepath).suffix.lower()
        if suffix in (".yaml", ".yml"):
            from .yaml_config import write_yaml_config

            write_yaml_config(filepath, self)
            return
        raise ValueError(
            f"Unsupported config format: {suffix!r}. Supported formats: .yaml, .yml"
        )

    def get(self, section, option, *, fallback=None, raw=False):
        """Get a value from ``section.option``.

        If ``raw`` is true, interpolation is not applied.
        """
        section_map = self._data.get(section)
        if not isinstance(section_map, dict):
            return fallback
        if option not in section_map:
            return fallback
        value = section_map[option]
        if raw:
            return value
        return self._resolve_value(
            value, current_section=section, stack=[(section, option)]
        )

    def sections(self):
        """Return top-level sections that are mappings."""
        return [k for k, v in self._data.items() if isinstance(v, dict)]

    def has_section(self, section):
        """Whether a section exists and is a mapping."""
        return isinstance(self._data.get(section), dict)

    def _resolve_mapping(self, value, *, current_section, stack):
        """
        Args:
            value (dict[str, Any]):
            current_section (str | None):
            stack (list[tuple[str, str]]):

        Returns:
            dict[str, Any]:
        """
        out: dict[str, Any] = {}
        for key, item in value.items():
            section_for_child = key if isinstance(item, dict) else current_section
            out[key] = self._resolve_value(
                item, current_section=section_for_child, stack=stack
            )
        return out

    def _resolve_value(self, value, *, current_section, stack):
        """
        Args:
        value (Any):
        current_section (str | None):
        stack (list[tuple[str, str]]):

        Returns:
        Any:
        """
        if isinstance(value, dict):
            return self._resolve_mapping(
                value, current_section=current_section, stack=stack
            )
        if isinstance(value, list):
            return [
                self._resolve_value(v, current_section=current_section, stack=stack)
                for v in value
            ]
        if not isinstance(value, str):
            return value

        def _resolve_token(token):
            token = token.strip()
            if "|" in token:
                section, option = token.split("|", 1)
                section = section.strip()
                option = option.strip()
            elif ":" in token:
                section, option = token.split(":", 1)
                section = section.strip()
                option = option.strip()
            else:
                if current_section is None:
                    raise ValueError(
                        f"Cannot resolve token '${{{token}}}' without a section context"
                    )
                section = current_section
                option = token
            key = (section, option)
            if key in stack:
                cycle = " -> ".join((f"{s}.{o}" for s, o in [*stack, key]))
                raise ValueError(f"Config interpolation cycle detected: {cycle}")
            target = self._lookup(section, option)
            if target is None:
                raise KeyError(f"Missing interpolation reference: {section}.{option}")
            return self._resolve_value(
                target, current_section=section, stack=[*stack, key]
            )

        exact_match = _TOKEN_RE.fullmatch(value)
        if exact_match:
            return _resolve_token(exact_match.group(1))

        def _replacement(match):
            return str(_resolve_token(match.group(1)))

        return _TOKEN_RE.sub(_replacement, value)

    def _lookup(self, section, option):
        """
        Args:
            section (str):
            option (str):

        Returns:
            Any | None:
        """
        section_map = self._data.get(section)
        if isinstance(section_map, dict) and option in section_map:
            return section_map[option]
        return None
