"""Core data types for GWAITH."""

from __future__ import annotations

from typing import Any

import numpy as np


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
        if isinstance(other, self.__class__):
            return self.__add__(other)
        return NotImplemented

    def __sub__(self, other: Series) -> Series:
        self._check_compatible(other)
        return self._new_from_data(self.data - other.data)

    def __rsub__(self, other: float | Series) -> Series:
        if isinstance(other, (float, int)):
            return self._new_from_data(other - self.data)
        elif isinstance(other, self.__class__):
            other._check_compatible(self)
            return other._new_from_data(other.data - self.data)
        return NotImplemented

    def __getitem__(self, key: int | slice) -> Any:
        """Preserve the series type for slices and return samples for indices."""
        if isinstance(key, slice):
            return self._new_from_data(self.data[key])
        return self.data[key]

    def __setitem__(self, key: int | slice, value: Any) -> None:
        self.data[key] = value

    def __iadd__(self, other: Series) -> Series:
        self._check_compatible(other)
        self.data += other.data
        return self

    def __mul__(self, other: float | Series) -> Series:
        if isinstance(other, (float, int)):
            return self._new_from_data(self.data * other)
        elif isinstance(other, self.__class__):
            self._check_compatible(other)
            return self._new_from_data(self.data * other.data)
        return NotImplemented

    def __rmul__(self, other: float | Series) -> Series:
        return self.__mul__(other)

    def __truediv__(self, other: float | Series) -> Series:
        if isinstance(other, (float, int)):
            return self._new_from_data(self.data / other)
        elif isinstance(other, self.__class__):
            self._check_compatible(other)
            return self._new_from_data(self.data / other.data)
        return NotImplemented

    def __rtruediv__(self, other: float | Series) -> Series:
        if isinstance(other, (float, int)):
            return self._new_from_data(other / self.data)
        elif isinstance(other, self.__class__):
            other._check_compatible(self)
            return other._new_from_data(other.data / self.data)
        return NotImplemented

    def __pow__(self, other: float | Series) -> Series:
        if isinstance(other, (float, int)):
            return self._new_from_data(self.data**other)
        elif isinstance(other, self.__class__):
            self._check_compatible(other)
            return self._new_from_data(self.data**other.data)
        return NotImplemented

    def __rpow__(self, other: float | Series) -> Series:
        if isinstance(other, (float, int)):
            return self._new_from_data(other**self.data)
        elif isinstance(other, self.__class__):
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

    def conj(self) -> Series:
        """Returns the complex conjugate of the series."""
        return self._new_from_data(np.conj(self.data))

    def astype(self, dtype: np.dtype) -> Series:
        """Casts the series to a specified type."""
        return self._new_from_data(self.data.astype(dtype))

    def abs(self) -> Series:
        """Returns a new Series with the absolute values of the data."""
        return self._new_from_data(np.abs(self.data))

    def __abs__(self) -> Series:
        """Supports the built-in abs() function."""
        return self.abs()

    def max(self) -> float:
        """Returns the maximum value of the data."""
        return self.data.max()

    def sum(self) -> float:
        """Returns the sum of the data."""
        return self.data.sum()

    def min(self) -> float:
        """Returns the minimum value of the data."""
        return self.data.min()

    def __iter__(self):
        """Supports iteration, enabling built-in max(), min(), sum()."""
        for i in range(len(self.data)):
            yield self.data[i]

    def copy(self) -> Series:
        """Returns a copy of the data."""
        return self._new_from_data(self.data.copy())
