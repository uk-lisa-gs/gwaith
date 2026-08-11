"""Tests for the Pegasus exporter functionality within generator module."""

import unittest.mock
from pathlib import Path

import pytest

from gwaith.workflow.generator import build_workflow


@pytest.fixture
def mock_gwaith_config():
    """Fixture to create a mock GwaithConfigParser object."""
    mock_config = unittest.mock.MagicMock()
    # The build_workflow function expects config_parser.data to be a dict
    # with workflow sections. Signal streams are identified by sections whose
    # name matches an entry in the "executables" section.
    mock_config.data = {
        "workflow": {
            "rounds": 1,
            "name": "test-workflow",
        },
        "processor": {
            "options": {}
        },
        "executables": {
            "sine_low": "/usr/local/bin/sine_low",
        },
        # This section name matches an executable, creating a signal stream
        "sine_low": {
            "options": {}
        },
    }

    def get_side_effect(section, option=None, **kwargs):
        if isinstance(option, str):
            return mock_config.data.get((section, option), kwargs.get("fallback"))
        return mock_config.data.get(section, option or kwargs.get("fallback"))

    mock_config.get.side_effect = get_side_effect
    return mock_config


def test_build_workflow_returns_gwaith_workflow(mock_gwaith_config):
    """Test the build_workflow function returns a GwaithWorkflow object."""
    workflow_name = "test-workflow"
    workflow_dir = Path("/tmp/workflow-dir")

    workflow = build_workflow(mock_gwaith_config, workflow_name, workflow_dir)

    # Check that a workflow object was created with expected attributes
    assert workflow is not None
    assert workflow.name == workflow_name
    assert Path(workflow.workflow_dir).resolve() == workflow_dir.resolve()
