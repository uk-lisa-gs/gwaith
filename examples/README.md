# Example Data Generation

This folder contains a reproducible generator for a simple 1-month synthetic dataset:
- non-white colored noise from a PSD model
- one constant offset
- five sine waves at distinct frequencies

All parameters are configured in `example_generation_config.yaml`.

## Run

From repository root:

```bash
python examples/generate_example_data.py
```

Or with a custom config:

```bash
python examples/generate_example_data.py --config path/to/config.yaml
```

## Outputs

By default files are written to `examples/example_data/`:
- `example_data.h5` with dataset `data` and attrs `epoch`, `delta_t`
- `example_truth.yaml` containing injected offset/sine parameters and metadata

Use `example_data.h5` as workflow input and estimate PSD during the workflow.

## Build Workflow Scripts

After generating `example_data.h5`, create workflow scripts with:

```bash
gwaith_build_workflow --config examples/workflow_config.yaml
```

This creates per-round bash files for:
- noise estimation
- offset fit
- sine fit
- residual combination/subtraction

It also creates final scripts for parameter consolidation and final noise
estimation, plus a master runner script (`run_workflow.sh`) in the generated
workflow directory.

## Universal Workflow Generator

Use the template-based workflow generator to emit scheduler-specific artifacts
from a split YAML definition. The top-level workflow topology is in
`workflow.yaml`; per-stream configs live under `streams/`:

```bash
gwaith_generate_universal_workflow \
  --config examples/workflow.yaml \
  --exporter slurm \
  --output-dir examples/generated_workflow
```

Replace `--exporter slurm` with `--exporter snakemake`, `--exporter htcondor`,
or `--exporter all` to target a different scheduler.

This generates:
- Slurm job scripts (`.sh` with `#SBATCH` headers)
- a Snakemake `Snakefile`
- HTCondor submit files (`.sub`)
