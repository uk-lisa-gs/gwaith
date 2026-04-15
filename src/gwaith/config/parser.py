"""Configuration parser with interpolation for YAML and INI files.

This module provides an in-repo alternative to external interpolating config
parsers and supports both YAML and INI definitions.
"""
import logging
import re
from pathlib import Path
from typing import Any

from .yaml_config import load_yaml_data
from .utils import safe_update, interpolate_dict

logger = logging.getLogger('gwaith.config.parser')

_DEFAULT_SECTION_KEYS = ('workflow', 'executables', 'default_resources')

class GwaithConfigParser:
    """Interpolation-capable parser for YAML and INI configuration files.

    Interpolation tokens:
    - ``${section:option}``
    - ``${section|option}``
    - ``${option}`` (resolved in the current section)
    """

    def __init__(self, args):
        """
        Args:
            input_file (str):

        Returns:
            None:
        """

        logger.info("Loading Config")
        self.input_files = args.config_files
        self.args = args
        self.file_types = self.config_file_types()
        self._data = self.read_config(args.config_files)
        self.normalise()

    @classmethod
    def from_cli(cls, args):
        """
        Args:
            args (argparse.Namespace):

        Returns:
            GwaithConfigParser:
        """
        return cls(args)


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
        return self._resolve_value(value, current_section=section, stack=[(section, option)])
    
    def sections(self):
        """Return top-level sections that are mappings."""
        return [k for k, v in self._data.items() if isinstance(v, dict)]
    
    def has_section(self, section):
        """Whether a section exists and is a mapping."""
        return isinstance(self._data.get(section), dict)

    # def _resolve_mapping(self, value, *, current_section, stack):
    #     """
    #     Args:
    #         value (dict[str, Any]):
    #         current_section (str | None):
    #         stack (list[tuple[str, str]]):

    #     Returns:
    #         dict[str, Any]:
    #     """
    #     out: dict[str, Any] = {}
    #     for key, item in value.items():
    #         section_for_child = key if isinstance(item, dict) else current_section
    #         out[key] = self._resolve_value(item, current_section=section_for_child, stack=stack)
    #     return out
    
    # def _resolve_value(self, value, *, current_section, stack):
    #     """
    #     Args:
    #         value (Any):
    #         current_section (str | None):
    #         stack (list[tuple[str, str]]):

    #     Returns:
    #         Any:
    #     """ 
    #     if isinstance(value, dict):
    #         return self._resolve_mapping(value, current_section=current_section, stack=stack)
    #     else:
    #         return value

    def config_file_types(self):
        """
        Returns:
            list of strings
        """
        if not self.input_files:
            return None
        file_types = []
        for input_file in self.input_files:
            sfx = Path(input_file).suffix.lower()
            if sfx in (".yaml", ".yml"):
                file_types.append("yaml")
            elif sfx in (".ini"):
                file_types.append("ini")
            else:
                raise ValueError("Unknown config file type")
        return file_types


    def read_config(self, _):
        config_dict = {}
        for input_file, file_type in zip(self.input_files, self.file_types):
            if file_type == "yaml":
                safe_update(
                    config_dict,
                    load_yaml_data(input_file)
                )
        return config_dict

    @property
    def data(self):
        return self._data

    def normalise(self) -> None:
        """Functions to normalise a configuration dictionary

        These functions will take in a dictionary of data in the format used by the GwaithConfigParser

        These will do things like:
         - interpolate values like ${section|value} and grab the value from section[options][value]
         - check that all of the defined sections have executables defined
         - add resources to all sections. this will use the default values if it isnt defined on a per-node basis
        """
        self._interpolate_values()
        self._apply_default_resources()
        self._check_executables()

    def _interpolate_values(self) -> None:
        """Interpolate values like ${section|value} and grab the value from section['options'][value]."""
        logger.debug('Interpolating values')
        
        interpolate_dict(self._data, self._data)

    def _apply_default_resources(self) -> None:
        """Add resources to all sections. This will use the default values if they are "
        "not already defined on a per-section basis."""
        logger.debug('Applying default resources to all sections')
        default_resources = self._data.get('default_resources', {})

        for section_name, section_data in self._data.items():
            # Skip known global/config level sections
            if section_name in _DEFAULT_SECTION_KEYS:
                logger.debug(f"Default resources: Skipping {section_name}")
                continue
            else:
                logger.debug(f"Default resources: {section_name}")

            if not isinstance(section_data, dict):
                section_data = {}

            if 'resources' not in section_data:
                section_data['resources'] = {}

            for res_key, res_val in default_resources.items():
                if res_key not in section_data['resources']:
                    section_data['resources'][res_key] = res_val

    def _check_executables(self) -> None:
        """Check that all of the defined sections have executables defined."""
        executable_keys = self._data['executables'].keys()
        for section_name, section_data in self._data.items():
            # Skip known global/config level sections
            if section_name in _DEFAULT_SECTION_KEYS:
                logger.debug(f"Executable check:skipping {section_name}")
                continue
            else:
                logger.debug(f"Executable check: {section_name}")

            if section_name not in executable_keys:
                raise ValueError(
                    f"Section '{section_name}' does not have an executable definition."
                )
