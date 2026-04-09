# GWAITH

GWAITH (Gravitational Wave Analysis Interface and Task Handler, pronounced /ɡwai̯θ/, g-why-th, Welsh for 'work') provides tools for gravitational-wave analysis pipelines.

## Current Tools

### `gwaith_estimate_psd`

Estimates the power spectral density (PSD) from data using Welch's method. Supports subtracting multiple signal timeseries before PSD estimation.

**Usage:**
```bash
gwaith_estimate_psd --data original.h5 --output psd.h5 [--signal signal1.h5 signal2.h5 ...]
```

**Options:**
- `--data`: HDF5 dataset file (required)
- `--data-dataset`: Dataset name in HDF5 file (default: 'data')
- `--signal`: HDF5 signal files to subtract (optional, multiple allowed)
- `--signal-dataset`: Dataset name in signal HDF5 files (default: 'signal')
- `--output`: Output HDF5 file for PSD (optional)
- `--output-dataset`: Dataset name in output HDF5 file (default: 'psd')
- `--fs`: Sampling frequency in Hz (default: 1.0)
- `--nperseg`: Segment length for Welch method (optional)
- `--noverlap`: Overlap length for Welch method (optional)
- `-v, --verbose`: Verbose output

**File Format:**
Input and output use HDF5. If no output file is specified, PSD frequencies and values are printed to stdout.
