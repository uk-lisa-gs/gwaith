from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.fft as fft

from .series import Series

if TYPE_CHECKING:
    from .timeseries import TimeSeries


class FrequencySeries(Series):
    """A frequency-domain series with GPS metadata.
    Parameters
    ----------
    data:
        Values at each frequency bin (e.g. PSD).
    delta_f:
        Frequency bin spacing (Hz).
    f0:
        Frequency of the first bin (Hz). Defaults to 0.
    epoch:
        GPS start time (seconds). Optional.
    """

    def __init__(
        self,
        data: np.ndarray,
        delta_f: float,
        f0: float = 0.0,
        epoch: float | None = None,
    ) -> None:
        super().__init__(data)
        self.f0 = float(f0)
        self.delta_f = float(delta_f)
        if epoch is not None:
            self.epoch = float(epoch)

    @property
    def sample_frequencies(self) -> np.ndarray:
        """Returns the frequency values."""
        return self.frequencies

    def __repr__(self) -> str:
        return (
            f"FrequencySeries(f0={self.f0}, delta_f={self.delta_f}, "
            f"n_bins={len(self.data)})"
        )

    @property
    def frequencies(self) -> np.ndarray:
        """Frequency values for each bin (Hz)."""
        return self.f0 + np.arange(len(self)) * self.delta_f

    def _check_compatible(self, other: FrequencySeries) -> None:
        super()._check_compatible(other)
        if self.f0 != other.f0:
            raise ValueError(f"f0 mismatch: {self.f0} != {other.f0}")
        if self.delta_f != other.delta_f:
            raise ValueError(
                f"delta_f mismatch: {self.delta_f} != {other.delta_f}"
            )

    def to_timeseries(self, delta_t: float = None) -> "TimeSeries":
        """Computes the inverse Fourier transform of the frequencyseries."""
        from .timeseries import TimeSeries

        n = (len(self.data) - 1) * 2
        if delta_t is None:
            # This is only valid if the frequency series was created from a
            # timeseries of length n.
            if self.delta_f == 0:
                raise ValueError("Cannot determine delta_t from delta_f=0")
            delta_t = 1 / (n * self.delta_f)

        ts_data = fft.irfft(self.data, n=n)
        epoch = getattr(self, "epoch", 0)
        return TimeSeries(ts_data, epoch, delta_t)

    def cyclic_time_shift(self, seconds: float) -> "FrequencySeries":
        """Cyclically shifts the frequencyseries by a given number of seconds."""
        phase_shift = np.exp(2j * np.pi * self.frequencies * seconds)
        shifted_data = self.data * phase_shift
        return self._new_from_data(shifted_data)

    def save(self, filepath: str, dataset_name: str | None = None, **attrs) -> None:
        """Write a FrequencySeries to file, auto-detecting format from extension."""
        from gwaith.io import write_frequencyseries
        write_frequencyseries(self, filepath, dataset_name, **attrs)

    @classmethod
    def load(cls, filepath: str, dataset_name: str | None = None) -> "FrequencySeries":
        """Load a FrequencySeries from file, auto-detecting format from extension."""
        from gwaith.io import load_frequencyseries
        return load_frequencyseries(filepath, dataset_name)