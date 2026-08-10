import numpy as np
import pytest

from gwaith.types import Series


class TestSeries:
    @pytest.fixture
    def series_class(self):
        return Series

    @pytest.fixture
    def series_data(self):
        return np.array([1.0, 2.0, 3.0, 4.0])

    @pytest.fixture
    def series(self, series_class, series_data):
        if series_class == Series:
            return series_class(series_data)
        elif series_class.__name__ == "TimeSeries":
            return series_class(series_data, epoch=0, delta_t=1)
        elif series_class.__name__ == "FrequencySeries":
            return series_class(series_data, f0=0, delta_f=1)

    def test_series_init(self, series, series_data):
        assert np.array_equal(series.data, series_data)

    def test_series_len(self, series, series_data):
        assert len(series) == len(series_data)

    def test_series_getitem(self, series, series_data):
        assert series[0] == series_data[0]
        assert np.array_equal(series[1:3], series_data[1:3])

    def test_series_setitem(self, series, series_data):
        series[0] = 10.0
        assert series[0] == 10.0
        series[1:3] = np.array([20.0, 30.0])
        series_data[0] = 10.0
        series_data[1:3] = np.array([20.0, 30.0])
        assert np.array_equal(series.data, series_data)

    def test_series_add(self, series_class, series_data):
        if series_class == Series:
            s1 = series_class(series_data)
            s2 = series_class(series_data)
            s_sum = s1 + s2
            assert np.array_equal(s_sum.data, series_data + series_data)
            assert isinstance(s_sum, series_class)
        elif series_class.__name__ == "TimeSeries":
            s1 = series_class(series_data, epoch=0, delta_t=1)
            s2 = series_class(series_data, epoch=0, delta_t=1)
            s_sum = s1 + s2
            assert np.array_equal(s_sum.data, series_data + series_data)
            assert isinstance(s_sum, series_class)
        elif series_class.__name__ == "FrequencySeries":
            s1 = series_class(series_data, f0=0, delta_f=1)
            s2 = series_class(series_data, f0=0, delta_f=1)
            s_sum = s1 + s2
            assert np.array_equal(s_sum.data, series_data + series_data)
            assert isinstance(s_sum, series_class)

    def test_series_mul_scalar(self, series, series_data):
        s_mul = series * 2.0
        assert np.array_equal(s_mul.data, series_data * 2.0)
        assert isinstance(s_mul, type(series))

    def test_series_real(self, series_class):
        series_data = np.array([1.0 + 1j, 2.0 + 2j, 3.0 + 3j])
        if series_class == Series:
            s = series_class(series_data)
        elif series_class.__name__ == "TimeSeries":
            s = series_class(series_data, epoch=0, delta_t=1)
        elif series_class.__name__ == "FrequencySeries":
            s = series_class(series_data, f0=0, delta_f=1)

        real_s = s.real()
        assert np.array_equal(real_s.data, np.array([1.0, 2.0, 3.0]))
        assert isinstance(real_s, series_class)
