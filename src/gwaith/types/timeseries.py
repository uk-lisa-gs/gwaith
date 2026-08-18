from __future__ import annotations

from typing import TYPE_CHECKING, Any

import h5py
import numpy as np
from numpy import fft

from .series import Series

if TYPE_CHECKING:
    from .frequencyseries import FrequencySeries


class TimeSeries(Series):
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
        super().__init__(data)
        self.epoch = epoch
        self.delta_t = delta_t

    @property
    def epoch(self) -> float:
        """GPS start time of the first sample (seconds)."""
        return self._epoch

    @epoch.setter
    def epoch(self, value: float) -> None:
        self._epoch = float(value)

    @property
    def delta_t(self) -> float:
        """Sample spacing (seconds)."""
        return self._delta_t

    @delta_t.setter
    def delta_t(self, value: float) -> None:
        self._delta_t = float(value)

    @property
    def sample_times(self) -> np.ndarray:
        """The sample times of the TimeSeries."""
        return self.epoch + np.arange(len(self.data)) * self.delta_t

    def __repr__(self) -> str:
        return (
            f"TimeSeries(epoch={self.epoch}, delta_t={self.delta_t}, "
            f"n_samples={len(self.data)})"
        )

    def __getitem__(self, key: int | slice) -> Any | TimeSeries:
        if isinstance(key, int):
            return self.data[key]
        elif isinstance(key, slice):
            start, _, step = key.indices(len(self.data))
            new_data = self.data[key]
            new_epoch = self.epoch + start * self.delta_t
            new_delta_t = self.delta_t * (step if step is not None else 1)
            return TimeSeries(new_data, new_epoch, new_delta_t)
        else:
            raise TypeError(f"Invalid key type: {type(key)}")

    def _check_compatible(self, other: TimeSeries) -> None:
        super()._check_compatible(other)
        if self.epoch != other.epoch:
            raise ValueError(f"epoch mismatch: {self.epoch} != {other.epoch}")
        if self.delta_t != other.delta_t:
            raise ValueError(f"delta_t mismatch: {self.delta_t} != {other.delta_t}")

    def to_timeseries(self) -> TimeSeries:
        """Returns a copy of the timeseries."""
        return TimeSeries(self.data, self.epoch, self.delta_t)

    def to_frequencyseries(self) -> FrequencySeries:
        """Computes the Fourier transform of the timeseries."""
        from .frequencyseries import FrequencySeries

        n = len(self.data)
        freq_data = fft.rfft(self.data)
        f0 = 0.0
        delta_f = 1.0 / (n * self.delta_t)
        return FrequencySeries(freq_data, delta_f=delta_f, f0=f0, epoch=self.epoch)

    def psd(self, segment_duration: float) -> FrequencySeries:
        """
        Estimates the power spectral density (PSD) of the timeseries using
        Welch's method.
        """
        from .frequencyseries import FrequencySeries

        segment_length = int(segment_duration / self.delta_t)
        if segment_length == 0:
            raise ValueError("Segment duration is smaller than sample spacing.")

        num_segments = (len(self.data) - segment_length // 2) // (segment_length // 2)
        if num_segments == 0:
            raise ValueError("Not enough data for a single segment.")

        psds = []
        for i in range(num_segments):
            start = i * (segment_length // 2)
            end = start + segment_length
            segment = self.data[start:end]
            window = np.hanning(segment_length)
            windowed_segment = segment * window
            ft = fft.rfft(windowed_segment)
            psd = np.abs(ft) ** 2
            psds.append(psd)

        avg_psd = np.mean(psds, axis=0)
        f0 = 0.0
        delta_f = 1.0 / (segment_length * self.delta_t)

        # Normalise
        # Hanning window squared and summed
        win_norm = np.sum(np.hanning(segment_length) ** 2)
        avg_psd *= 2 / (win_norm * (1 / self.delta_t))

        return FrequencySeries(avg_psd, delta_f=delta_f, f0=f0, epoch=self.epoch)

    def cyclic_time_shift(self, seconds: float) -> TimeSeries:
        """Cyclically shifts the timeseries by a given number of seconds."""
        shift = int(seconds / self.delta_t)
        shifted_data = np.roll(self.data, shift)
        return TimeSeries(shifted_data, self.epoch, self.delta_t)

    def save(self, filepath: str, dataset_name: str | None = None) -> None:
        """Write a TimeSeries to an HDF5 file.

        Parameters
        ----------
        filepath : str
            Path to the HDF5 file.
        dataset_name : str or None, optional
            Name of the group to save the TimeSeries into within the file.
            If None, defaults to 'timeseries'.
        """
        name = "timeseries" if dataset_name is None else dataset_name
        with h5py.File(filepath, "a") as f:
            if name in f:
                del f[name]
            group = f.create_group(name)
            group.create_dataset("data", data=self.data)
            group.attrs["epoch"] = self.epoch
            group.attrs["delta_t"] = self.delta_t

    @classmethod
    def load(cls, filepath: str, dataset_name: str | None = None) -> TimeSeries:
        """Load a TimeSeries from an HDF5 file.

        Parameters
        ----------
        filepath : str
            Path to the HDF5 file.
        dataset_name : str or None, optional
            Name of the group to load the TimeSeries from within the file.
            If None, defaults to 'timeseries'.
        """
        name = "timeseries" if dataset_name is None else dataset_name
        with h5py.File(filepath, "r") as f:
            group = f[name]
            data = group["data"][:]
            epoch = group.attrs["epoch"]
            delta_t = group.attrs["delta_t"]
        return cls(data, epoch, delta_t)
