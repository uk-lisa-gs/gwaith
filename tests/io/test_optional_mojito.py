"""Exercise core I/O in a fresh interpreter without optional backends."""

import subprocess
import sys
import textwrap


def test_core_io_without_mojito(tmp_path):
    script = textwrap.dedent(
        """
        import importlib.abc
        import sys
        from pathlib import Path
        import numpy as np

        class BlockMojito(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split('.')[0] in {'mojito', 'MojitoProcessor'}:
                    raise ModuleNotFoundError(
                        f'No module named {fullname!r}', name=fullname
                    )

        sys.meta_path.insert(0, BlockMojito())
        from gwaith.io import (
            load_timeseries, write_timeseries,
            write_mojito_tdis, write_mojito_orbits,
        )
        from gwaith.process.mojito import process_mojito
        from tools.data import ingest_data
        from gwaith.types import TimeSeries

        path = Path(sys.argv[1]) / 'series.hdf5'
        original = TimeSeries(np.arange(4.0), epoch=12.0, delta_t=0.5)
        write_timeseries(original, path)
        loaded = load_timeseries(path)
        np.testing.assert_array_equal(loaded.data, original.data)
        assert loaded.epoch == original.epoch
        assert loaded.delta_t == original.delta_t

        for operation in (
            lambda: write_mojito_tdis({'X': original}, path),
            lambda: write_mojito_orbits(object(), path),
            lambda: process_mojito(path, {}),
        ):
            try:
                operation()
            except ModuleNotFoundError as exc:
                assert exc.name == 'mojito'
            else:
                raise AssertionError('Optional backend must require Mojito')
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
