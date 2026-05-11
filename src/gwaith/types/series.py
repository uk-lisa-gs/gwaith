"""Core data types for GWAITH."""

from __future__ import annotations

import numpy as np


class TimeSeries:
    """A uniformly-sampled timeseries with GPS metadata.

    Parameters
    ----------
    data:
        Sample values.
    epoch:
        GPS start time of the first sample (seconds).
    delta_t:
        Sample spacing (seconds).
    """

    def __init__(self, data: np.ndarray, epoch: float, delta_t: float) -> None:
        self.data = np.asarray(data)
        self.epoch = float(epoch)
        self.delta_t = float(delta_t)

    def __repr__(self) -> str:
        return (
            f"TimeSeries(epoch={self.epoch}, delta_t={self.delta_t}, "
            f"n_samples={len(self.data)})"
        )

    def _check_compatible(self, other: TimeSeries) -> None:
        if self.epoch != other.epoch:
            raise ValueError(f"epoch mismatch: {self.epoch} != {other.epoch}")
        if self.delta_t != other.delta_t:
            raise ValueError(f"delta_t mismatch: {self.delta_t} != {other.delta_t}")

    def __add__(self, other: TimeSeries) -> TimeSeries:
        self._check_compatible(other)
        return TimeSeries(self.data + other.data, self.epoch, self.delta_t)

    def __radd__(self, other: TimeSeries) -> TimeSeries:
        return self.__add__(other)

    def __sub__(self, other: TimeSeries) -> TimeSeries:
        self._check_compatible(other)
        return TimeSeries(self.data - other.data, self.epoch, self.delta_t)

    def __rsub__(self, other: TimeSeries) -> TimeSeries:
        if isinstance(other, TimeSeries):
            other._check_compatible(self)
            return TimeSeries(other.data - self.data, self.epoch, self.delta_t)
        return NotImplemented


class FrequencySeries:
    """A frequency-domain series with GPS metadata.

    Parameters
    ----------
    data:
        Values at each frequency bin (e.g. PSD).
    frequencies:
        Frequency values corresponding to each bin (Hz).
    epoch:
        GPS start time of the parent timeseries (seconds).
    delta_t:
        Sample spacing of the parent timeseries (seconds).
    """

    def __init__(
        self,
        data: np.ndarray,
        frequencies: np.ndarray,
        epoch: float,
        delta_t: float,
    ) -> None:
        self.data = np.asarray(data)
        self.frequencies = np.asarray(frequencies)
        self.epoch = float(epoch)
        self.delta_t = float(delta_t)

    def __repr__(self) -> str:
        return (
            f"FrequencySeries(epoch={self.epoch}, delta_t={self.delta_t}, "
            f"delta_f={self.delta_f:.6g}, n_bins={len(self.data)})"
        )

    @property
    def delta_f(self) -> float:
        """Frequency bin spacing (Hz), derived from the ``frequencies`` array."""
        if len(self.frequencies) < 2:
            raise ValueError("Cannot compute delta_f: fewer than 2 frequency bins")
        return float(self.frequencies[1] - self.frequencies[0])

    def _check_compatible(self, other: FrequencySeries) -> None:
        if self.delta_f != other.delta_f:
            raise ValueError(f"delta_f mismatch: {self.delta_f} != {other.delta_f}")

    def __mul__(self, other: FrequencySeries) -> FrequencySeries:
        self._check_compatible(other)
        return FrequencySeries(
            self.data * other.data, self.frequencies, self.epoch, self.delta_t
        )

    def __rmul__(self, other: FrequencySeries) -> FrequencySeries:
        return self.__mul__(other)

    def __truediv__(self, other: FrequencySeries) -> FrequencySeries:
        self._check_compatible(other)
        return FrequencySeries(
            self.data / other.data, self.frequencies, self.epoch, self.delta_t
        )

    def __rtruediv__(self, other: FrequencySeries) -> FrequencySeries:
        if isinstance(other, FrequencySeries):
            other._check_compatible(self)
            return FrequencySeries(
                other.data / self.data, self.frequencies, self.epoch, self.delta_t
            )
        return NotImplemented
