"""Compare workflow-recovered parameters with ground truth values.

This script loads the ground truth parameters used to generate example data
and the final consolidated parameters estimated by the workflow, then compares
them to assess recovery accuracy.
"""
import argparse
import logging
from pathlib import Path
from typing import Any
import yaml
from gwaith import init_logging
logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[1]

def load_yaml(path):
    """Load a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f) or {}

def compare_scalars(truth_value, estimated_value, param_name, tolerance=1e-06):
    """Compare two scalar values and return (matches, description)."""
    if isinstance(truth_value, (int, float)) and isinstance(estimated_value, (int, float)):
        abs_error = abs(truth_value - estimated_value)
        rel_error = abs_error / abs(truth_value) if truth_value != 0.0 else abs_error
        matches = abs_error <= tolerance or rel_error <= 0.001
        symbol = 'OK' if matches else 'FAIL'
        description = f'{symbol} {param_name}: truth={truth_value:.6e}, estimated={estimated_value:.6e}, error={abs_error:.6e}'
        if not matches:
            description += f' [REL_ERROR={rel_error:.3e}]'
        return (matches, description)
    else:
        return (False, f'FAIL {param_name}: type mismatch (truth={type(truth_value)}, estimated={type(estimated_value)})')

def compare_results(truth_path, workflow_path):
    """Compare truth and workflow results.

    Returns 0 if all comparisons pass, 1 if any comparisons fail.
    """
    truth = load_yaml(truth_path)
    workflow = load_yaml(workflow_path)
    logger.info('WORKFLOW RESULT COMPARISON')
    all_passed = True
    logger.info('### OFFSET RECOVERY')
    truth_offset = truth['signal']['offset']['value']
    estimated_offset = workflow['module_outputs']['offset']
    passed, msg = compare_scalars(truth_offset, estimated_offset, 'offset')
    logger.info(msg)
    all_passed = all_passed and passed
    logger.info('### SINE WAVE RECOVERY')
    truth_waves = truth['signal']['sine_waves']
    estimated_waves = workflow['module_outputs']['sine']['sine_waves']
    if len(truth_waves) != len(estimated_waves):
        logger.warning(f'Wave count mismatch: truth={len(truth_waves)}, estimated={len(estimated_waves)}')
        all_passed = False
    else:
        for i, (truth_w, est_w) in enumerate(zip(truth_waves, estimated_waves)):
            logger.info(f"Wave {i} (ID={truth_w['identifier']}):")
            passed, msg = compare_scalars(truth_w['amplitude'], est_w['amplitude'], f'  amplitude', tolerance=0.0001)
            logger.info(msg)
            all_passed = all_passed and passed
            passed, msg = compare_scalars(truth_w['frequency'], est_w['frequency'], f'  frequency', tolerance=1e-06)
            logger.info(msg)
            all_passed = all_passed and passed
            passed, msg = compare_scalars(truth_w['phase'], est_w['phase'], f'  phase', tolerance=0.01)
            logger.info(msg)
            all_passed = all_passed and passed
    logger.info('### NOISE PSD CONFIGURATION')
    truth_psd = truth['noise_psd']
    logger.info(f"Truth: amp={truth_psd['amplitude']}, floor={truth_psd['floor']}, f_knee={truth_psd['f_knee']}, slope={truth_psd['slope']}")
    if all_passed:
        logger.info('OK: ALL COMPARISONS PASSED')
        exit_code = 0
    else:
        logger.warning('FAIL: SOME COMPARISONS FAILED')
        exit_code = 1
    return exit_code

def main(argv=None):
    '''"""
Args:
    argv (list[str] | None):

Returns:
    int:
"""'''
    parser = argparse.ArgumentParser(prog='compare_workflow_results', description='Compare workflow-recovered parameters with ground truth.')
    parser.add_argument('--truth', default=str(REPO_ROOT / 'examples' / 'example_data' / 'example_truth.yaml'), help='Path to truth parameters file')
    parser.add_argument('--workflow', default=str(REPO_ROOT / 'examples' / 'workflow_out' / 'demo_workflow' / 'final' / 'final_consolidated_params.yaml'), help='Path to workflow consolidated parameters file')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Logging level')
    args = parser.parse_args(argv)
    init_logging(1)
    return compare_results(args.truth, args.workflow)
if __name__ == '__main__':
    exit(main())
