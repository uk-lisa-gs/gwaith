"""Core data types for GWAITH."""

from __future__ import annotations

from typing import Any, Union

import numpy as np
import numpy.fft as fft


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

    @property
    def sample_times(self) -> np.ndarray:
        """The sample times of the TimeSeries."""
        return self.epoch + np.arange(len(self.data)) * self.delta_t

    @property
    def dtype(self) -> np.dtype:
        """The data type of the underlying data."""
        return self.data.dtype

    def __repr__(self) -> str:
        return (
            f"TimeSeries(epoch={self.epoch}, delta_t={self.delta_t}, "
            f"n_samples={len(self.data)})"
        )

    def _check_compatible(self, other: TimeSeries) -> None:
        if self.epoch != other.epoch:
            raise ValueError(f"epoch mismatch: {self.epoch} != {other.epoch}")
        if self.delta_t != other.delta_t:
            raise ValueError(
                f"delta_t mismatch: {self.delta_t} != {other.delta_t}"
            )
        if len(self) != len(other):
            raise ValueError(f"length mismatch: {len(self)} != {len(other)}")

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
            return TimeSeries(
                other.data - self.data,
                self.epoch,
                self.delta_t,
            )
        return NotImplemented

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key: Union[int, slice]) -> Any:
        return self.data[key]

    def __setitem__(self, key: Union[int, slice], value: Any) -> None:
        self.data[key] = value

    def __iadd__(self, other: TimeSeries) -> TimeSeries:
        self._check_compatible(other)
        self.data += other.data
        return self

    def __mul__(self, other: Union[float, int, TimeSeries]) -> TimeSeries:
        if isinstance(other, (float, int)):
            return TimeSeries(self.data * other, self.epoch, self.delta_t)
        if isinstance(other, TimeSeries):
            self._check_compatible(other)
            return TimeSeries(self.data * other.data, self.epoch, self.delta_t)
        return NotImplemented

    def to_frequencyseries(self) -> "FrequencySeries":
        """Computes the Fourier transform of the timeseries."""
        n = len(self.data)
        freq_data = fft.rfft(self.data)
        frequencies = fft.rfftfreq(n, d=self.delta_t)
        return FrequencySeries(freq_data, frequencies, self.epoch, self.delta_t)

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
        frequencies = fft.rfftfreq(segment_length, d=self.delta_t)
        
        # Normalise
        # Hanning window squared and summed
        win_norm = np.sum(np.hanning(segment_length)**2)
        avg_psd *= 2 / (win_norm * (1/self.delta_t))


        return FrequencySeries(avg_psd, frequencies, self.epoch, self.delta_t)

    def resize(self, new_size: int) -> None:
        """Resizes the timeseries data array."""
        self.data.resize(new_size, refcheck=False)

    def cyclic_time_shift(self, seconds: float) -> "TimeSeries":
        """Cyclically shifts the timeseries by a given number of seconds."""
        shift = int(seconds / self.delta_t)
        shifted_data = np.roll(self.data, shift)
        return TimeSeries(shifted_data, self.epoch, self.delta_t)

    def real(self) -> "TimeSeries":
        """Returns the real part of the timeseries."""
        return TimeSeries(np.real(self.data), self.epoch, self.delta_t)


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

    @property
    def sample_frequencies(self) -> np.ndarray:
        """Returns the frequency values."""
        return self.frequencies

    @property
    def dtype(self) -> np.dtype:
        """The data type of the underlying data."""
        return self.data.dtype

    def __repr__(self) -> str:
        return (
            f"FrequencySeries(epoch={self.epoch}, delta_t={self.delta_t}, "
            f"delta_f={self.delta_f:.6g}, n_bins={len(self.data)})"
        )

    @property
    def delta_f(self) -> float:
        """Frequency bin spacing (Hz).
        Derived from the ``frequencies`` array.
        """
        if len(self.frequencies) < 2:
            return 1 / (2 * self.delta_t * (len(self.data)-1)) if len(self.data) > 1 else 0

        return float(self.frequencies[1] - self.frequencies[0])

    def _check_compatible(self, other: FrequencySeries) -> None:
        if self.delta_f != other.delta_f:
            raise ValueError(
                f"delta_f mismatch: {self.delta_f} != {other.delta_f}"
            )

    def __mul__(self, other: Union[float, int, "FrequencySeries"]) -> "FrequencySeries":
        if isinstance(other, (float, int)):
            return FrequencySeries(self.data * other, self.frequencies, self.epoch, self.delta_t)
        if isinstance(other, FrequencySeries):
            self._check_compatible(other)
            return FrequencySeries(
                self.data * other.data, self.frequencies, self.epoch, self.delta_t
            )
        return NotImplemented

    def __rmul__(self, other: FrequencySeries) -> FrequencySeries:
        return self.__mul__(other)

    def __truediv__(self, other: Union[float, int, "FrequencySeries"]) -> "FrequencySeries":
        if isinstance(other, (float, int)):
            return FrequencySeries(self.data / other, self.frequencies, self.epoch, self.delta_t)
        if isinstance(other, FrequencySeries):
            self._check_compatible(other)
            return FrequencySeries(
                self.data / other.data, self.frequencies, self.epoch, self.delta_t
            )
        return NotImplemented

    def __rtruediv__(self, other: FrequencySeries) -> FrequencySeries:
        if isinstance(other, FrequencySeries):
            other._check_compatible(self)
            return FrequencySeries(
                other.data / self.data,
                self.frequencies,
                self.epoch,
                self.delta_t,
            )
        return NotImplemented

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key: Union[int, slice]) -> Any:
        return self.data[key]

    def __setitem__(self, key: Union[int, slice], value: Any) -> None:
        self.data[key] = value

    def __pow__(self, power: float) -> "FrequencySeries":
        return FrequencySeries(
            self.data**power, self.frequencies, self.epoch, self.delta_t
        )

    def to_timeseries(self, delta_t: float = None) -> "TimeSeries":
        """Computes the inverse Fourier transform of the frequencyseries."""
        if delta_t is None:
            delta_t = self.delta_t
        
        n = (len(self.data) - 1) * 2
        ts_data = fft.irfft(self.data, n=n)
        return TimeSeries(ts_data, self.epoch, delta_t)

    def save(self, filename: str) -> None:
        """Saves the frequency series data to a file."""
        np.savez(filename, data=self.data, frequencies=self.frequencies, epoch=self.epoch, delta_t=self.delta_t)

    def cyclic_time_shift(self, seconds: float) -> "FrequencySeries":
        """Cyclically shifts the frequencyseries by a given number of seconds."""
        phase_shift = np.exp(2j * np.pi * self.frequencies * seconds)
        shifted_data = self.data * phase_shift
        return FrequencySeries(shifted_data, self.frequencies, self.epoch, self.delta_t)

    def conj(self) -> "FrequencySeries":
        """Returns the complex conjugate of the frequencyseries."""
        return FrequencySeries(np.conj(self.data), self.frequencies, self.epoch, self.delta_t)

    def resize(self, new_size: int) -> None:
        """Resizes the frequency series data array."""
        self.data.resize(new_size, refcheck=False)
        self.frequencies.resize(new_size, refcheck=False)


    def astype(self, dtype: np.dtype) -> "FrequencySeries":
        """Casts the frequencyseries to a specified type."""
        return FrequencySeries(self.data.astype(dtype), self.frequencies, self.epoch, self.delta_t)

    def abs(self) -> "FrequencySeries":
        """Returns a new FrequencySeries with the absolute values of the data."""
        return FrequencySeries(np.abs(self.data), self.frequencies, self.epoch, self.delta_t)

    def max(self) -> float:
        """Returns the maximum value of the data."""
        return self.data.max()

    def sum(self) -> float:
        """Returns the sum of the data."""
        return self.data.sum()

    def min(self) -> float:
        """Returns the minimum value of the data."""
        return self.data.min()
