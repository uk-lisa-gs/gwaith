"""Core data types for GWAITH."""

from __future__ import annotations

from typing import Any, Union

import numpy as np
import numpy.fft as fft

class Series:
    """A base class for series data."""

    def __init__(self, data: np.ndarray) -> None:
        self.data = np.asarray(data)

    @property
    def dtype(self) -> np.dtype:
        """The data type of the underlying data."""
        return self.data.dtype

    def __len__(self) -> int:
        """The number of samples in the series data."""
        return len(self.data)

    def _check_compatible(self, other: Series) -> None:
        if len(self) != len(other):
            raise ValueError(f"length mismatch: {len(self)} != {len(other)}")

    def _new_from_data(self, data: np.ndarray) -> Series:
        """Create a new series of the same type with new data."""
        new_obj = self.__class__.__new__(self.__class__)
        new_obj.__dict__.update(self.__dict__)
        new_obj.data = np.asarray(data)
        return new_obj

    def __add__(self, other: Series) -> Series:
        self._check_compatible(other)
        return self._new_from_data(self.data + other.data)

    def __radd__(self, other: Series) -> Series:
        if other == 0:
            return self
        if isinstance(other, Series):
            return self.__add__(other)
        return NotImplemented

    def __sub__(self, other: Series) -> Series:
        self._check_compatible(other)
        return self._new_from_data(self.data - other.data)

    def __rsub__(self, other: Union[float, int, Series]) -> Series:
        if isinstance(other, (float, int)):
            return self._new_from_data(other - self.data)
        elif isinstance(other, Series):
            other._check_compatible(self)
            return other._new_from_data(other.data - self.data)
        return NotImplemented

    def __getitem__(self, key: Union[int, slice]) -> Any:
        return self.data[key]

    def __setitem__(self, key: Union[int, slice], value: Any) -> None:
        self.data[key] = value

    def __iadd__(self, other: Series) -> Series:
        self._check_compatible(other)
        self.data += other.data
        return self

    def __mul__(self, other: Union[float, int, Series]) -> Series:
        if isinstance(other, (float, int)):
            return self._new_from_data(self.data * other)
        elif isinstance(other, Series):
            self._check_compatible(other)
            return self._new_from_data(self.data * other.data)
        return NotImplemented
    
    def __rmul__(self, other: Union[float, int, Series]) -> Series:
        return self.__mul__(other)

    def __truediv__(self, other: Union[float, int, Series]) -> Series:
        if isinstance(other, (float, int)):
            return self._new_from_data(self.data / other)
        elif isinstance(other, Series):
            self._check_compatible(other)
            return self._new_from_data(self.data / other.data)
        return NotImplemented

    def __rtruediv__(self, other: Union[float, int, Series]) -> Series:
        if isinstance(other, (float, int)):
            return self._new_from_data(other / self.data)
        elif isinstance(other, Series):
            other._check_compatible(self)
            return other._new_from_data(other.data / self.data)
        return NotImplemented

    def __pow__(self, other: Union[float, int, Series]) -> "Series":
        if isinstance(other, (float, int)):
            return self._new_from_data(self.data**other)
        elif isinstance(other, Series):
            self._check_compatible(other)
            return self._new_from_data(self.data**other.data)
        return NotImplemented

    def __rpow__(self, other: Union[float, int, Series]) -> "Series":
        if isinstance(other, (float, int)):
            return self._new_from_data(other**self.data)
        elif isinstance(other, Series):
            other._check_compatible(self)
            return other._new_from_data(other.data**self.data)
        return NotImplemented

    def resize(self, new_size: int) -> None:
        """Resizes the data array."""
        self.data.resize(new_size, refcheck=False)

    def real(self) -> Series:
        """Returns the real part of the series."""
        return self._new_from_data(np.real(self.data))

    def imag(self) -> Series:
        """Returns the imaginary part of the series."""
        return self._new_from_data(np.imag(self.data))

    def conj(self) -> "Series":
        """Returns the complex conjugate of the series."""
        return self._new_from_data(np.conj(self.data))

    def astype(self, dtype: np.dtype) -> "Series":
        """Casts the series to a specified type."""
        return self._new_from_data(self.data.astype(dtype))

    def abs(self) -> "Series":
        """Returns a new Series with the absolute values of the data."""
        return self._new_from_data(np.abs(self.data))

    def max(self) -> float:
        """Returns the maximum value of the data."""
        return self.data.max()

    def sum(self) -> float:
        """Returns the sum of the data."""
        return self.data.sum()

    def min(self) -> float:
        """Returns the minimum value of the data."""
        return self.data.min()


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
        self.epoch = float(epoch)
        self.delta_t = float(delta_t)

    @property
    def sample_times(self) -> np.ndarray:
        """The sample times of the TimeSeries."""
        return self.epoch + np.arange(len(self.data)) * self.delta_t

    def __repr__(self) -> str:
        return (
            f"TimeSeries(epoch={self.epoch}, delta_t={self.delta_t}, "
            f"n_samples={len(self.data)})"
        )

    def _check_compatible(self, other: TimeSeries) -> None:
        super()._check_compatible(other)
        if self.epoch != other.epoch:
            raise ValueError(f"epoch mismatch: {self.epoch} != {other.epoch}")
        if self.delta_t != other.delta_t:
            raise ValueError(
                f"delta_t mismatch: {self.delta_t} != {other.delta_t}"
            )

    def to_timeseries(self) -> "TimeSeries":
        """Returns a copy of the timeseries."""
        return TimeSeries(self.data, self.epoch, self.delta_t)

    def to_frequencyseries(self) -> "FrequencySeries":
        """Computes the Fourier transform of the timeseries."""
        n = len(self.data)
        freq_data = fft.rfft(self.data)
        f0 = 0.0
        delta_f = 1.0 / (n * self.delta_t)
        fs = FrequencySeries(freq_data, f0=f0, delta_f=delta_f)
        # Stash epoch for round-tripping
        fs.epoch = self.epoch
        return fs

    def psd(self, segment_duration: float) -> "FrequencySeries":
        """
        Estimates the power spectral density (PSD) of the timeseries using
        Welch's method.
        """
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
        win_norm = np.sum(np.hanning(segment_length)**2)
        avg_psd *= 2 / (win_norm * (1/self.delta_t))

        fs = FrequencySeries(avg_psd, f0=f0, delta_f=delta_f)
        fs.epoch = self.epoch  # Stash epoch
        return fs

    def cyclic_time_shift(self, seconds: float) -> "TimeSeries":
        """Cyclically shifts the timeseries by a given number of seconds."""
        shift = int(seconds / self.delta_t)
        shifted_data = np.roll(self.data, shift)
        return TimeSeries(shifted_data, self.epoch, self.delta_t)


class FrequencySeries(Series):
    """A frequency-domain series with GPS metadata.
    Parameters
    ----------
    data:
        Values at each frequency bin (e.g. PSD).
    f0:
        Frequency of the first bin (Hz).
    delta_f:
        Frequency bin spacing (Hz).
    """

    def __init__(
        self,
        data: np.ndarray,
        f0: float,
        delta_f: float,
    ) -> None:
        super().__init__(data)
        self.f0 = float(f0)
        self.delta_f = float(delta_f)

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
        n = (len(self.data) - 1) * 2
        if delta_t is None:
            # This is only valid if the frequency series was created from a
            # timeseries of length n.
            if self.delta_f == 0:
                raise ValueError("Cannot determine delta_t from delta_f=0")
            delta_t = 1 / (n * self.delta_f)

        ts_data = fft.irfft(self.data, n=n)
        # Epoch is lost in this conversion unless it's stored explicitly.
        # For now, we assume an epoch of 0. A more robust solution might be
        # to carry epoch as optional metadata.
        epoch = getattr(self, "epoch", 0)
        return TimeSeries(ts_data, epoch, delta_t)

    def save(self, filename: str) -> None:
        """Saves the frequency series data to a file."""
        np.savez(filename, data=self.data, f0=self.f0, delta_f=self.delta_f)

    def cyclic_time_shift(self, seconds: float) -> "FrequencySeries":
        """Cyclically shifts the frequencyseries by a given number of seconds."""
        phase_shift = np.exp(2j * np.pi * self.frequencies * seconds)
        shifted_data = self.data * phase_shift
        return self._new_from_data(shifted_data)
