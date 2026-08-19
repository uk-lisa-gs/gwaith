import numpy as np
import pytest

from gwaith.types import FrequencySeries, TimeSeries
from .test_series import TestSeries


def test_timeseries_init():
    data = np.array([1.0, 2.0, 3.0])
    epoch = 100.0
    delta_t = 0.1
    ts = TimeSeries(data, epoch, delta_t)

    assert np.array_equal(ts.data, data)
    assert ts.epoch == epoch
    assert ts.delta_t == delta_t


def test_timeseries_sample_times():
    data = np.array([1.0, 2.0, 3.0])
    epoch = 100.0
    delta_t = 0.1
    ts = TimeSeries(data, epoch, delta_t)

    expected_sample_times = np.array([100.0, 100.1, 100.2])
    assert np.array_equal(ts.sample_times, expected_sample_times)


def test_timeseries_dtype():
    data = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    epoch = 100.0
    delta_t = 0.1
    ts = TimeSeries(data, epoch, delta_t)

    assert ts.dtype == np.float32


def test_timeseries_len():
    data = np.array([1.0, 2.0, 3.0, 4.0])
    ts = TimeSeries(data, 0.0, 1.0)
    assert len(ts) == 4


def test_timeseries_getitem():
    data = np.array([1.0, 2.0, 3.0, 4.0])
    ts = TimeSeries(data, 0.0, 1.0)
    assert ts[0] == 1.0
    assert np.array_equal(ts[1:3], np.array([2.0, 3.0]))


def test_timeseries_setitem():
    data = np.array([1.0, 2.0, 3.0])
    ts = TimeSeries(data, 0.0, 1.0)
    ts[0] = 10.0
    assert ts[0] == 10.0
    ts[1:3] = np.array([20.0, 30.0])
    assert np.array_equal(ts.data, np.array([10.0, 20.0, 30.0]))


def test_timeseries_add():
    ts1 = TimeSeries(np.array([1.0, 2.0]), 0.0, 1.0)
    ts2 = TimeSeries(np.array([3.0, 4.0]), 0.0, 1.0)
    ts_sum = ts1 + ts2
    assert np.array_equal(ts_sum.data, np.array([4.0, 6.0]))
    assert ts_sum.epoch == 0.0
    assert ts_sum.delta_t == 1.0


def test_timeseries_iadd():
    ts1 = TimeSeries(np.array([1.0, 2.0]), 0.0, 1.0)
    ts2 = TimeSeries(np.array([3.0, 4.0]), 0.0, 1.0)
    ts1 += ts2
    assert np.array_equal(ts1.data, np.array([4.0, 6.0]))


def test_timeseries_mul_scalar():
    ts = TimeSeries(np.array([1.0, 2.0]), 0.0, 1.0)
    ts_mul = ts * 2.0
    assert np.array_equal(ts_mul.data, np.array([2.0, 4.0]))


def test_timeseries_mul_timeseries():
    ts1 = TimeSeries(np.array([1.0, 2.0]), 0.0, 1.0)
    ts2 = TimeSeries(np.array([3.0, 4.0]), 0.0, 1.0)
    ts_mul = ts1 * ts2
    assert np.array_equal(ts_mul.data, np.array([3.0, 8.0]))


def test_timeseries_to_frequencyseries():
    data = np.array([0.0, 1.0, 0.0, -1.0, 0.0])
    ts = TimeSeries(data, 0.0, 1.0)
    fs = ts.to_frequencyseries()

    assert isinstance(fs, FrequencySeries)
    assert len(fs.data) == len(np.fft.rfft(data))
    assert fs.epoch == ts.epoch


def test_timeseries_psd():
    # Create a simple time series with a known frequency component
    delta_t = 0.01
    t = np.arange(0, 10, delta_t)  # 10 seconds of data
    frequency = 5.0  # Hz
    data = np.sin(2 * np.pi * frequency * t) + np.random.normal(0, 0.1, len(t))
    ts = TimeSeries(data, 0.0, delta_t)

    segment_duration = 1.0  # 1 second segments
    fs_psd = ts.psd(segment_duration)

    assert isinstance(fs_psd, FrequencySeries)
    # Check that the peak frequency is around 5Hz
    max_idx = np.argmax(np.abs(fs_psd.data))
    estimated_freq = fs_psd.frequencies[max_idx]
    # Allow for some tolerance due to Welch's method and windowing
    assert estimated_freq == pytest.approx(frequency, rel=0.1)


def test_timeseries_resize():
    data = np.array([1.0, 2.0, 3.0])
    ts = TimeSeries(data, 0.0, 1.0)
    ts.resize(5)
    assert len(ts.data) == 5
    assert np.array_equal(ts.data, np.array([1.0, 2.0, 3.0, 0.0, 0.0]))


def test_timeseries_epoch_assignment_coerces_to_float():
    ts = TimeSeries(np.array([1.0, 2.0, 3.0]), 0.0, 1.0)

    # Assigning a numpy scalar must be stored as a plain Python float so it
    # can never leak into HDF5 attributes as a compound dtype.
    ts.epoch = np.float64(100.0)
    assert isinstance(ts.epoch, float)
    assert not isinstance(ts.epoch, np.floating)
    assert ts.epoch == 100.0

    # sample_times must reflect the new epoch immediately.
    assert ts.sample_times[0] == 100.0
    assert np.array_equal(ts.sample_times, np.array([100.0, 101.0, 102.0]))


def test_timeseries_delta_t_assignment_coerces_to_float():
    ts = TimeSeries(np.array([1.0, 2.0, 3.0]), 0.0, 1.0)

    ts.delta_t = np.float64(0.5)
    assert isinstance(ts.delta_t, float)
    assert not isinstance(ts.delta_t, np.floating)
    assert ts.delta_t == 0.5


def test_timeseries_cyclic_time_shift():
    data = np.array([1.0, 2.0, 3.0, 4.0])
    ts = TimeSeries(data, 0.0, 1.0)
    shifted_ts = ts.cyclic_time_shift(2.0)  # Shift by 2 seconds (2 samples)
    assert np.array_equal(shifted_ts.data, np.array([3.0, 4.0, 1.0, 2.0]))
    # The cyclic shift must preserve the start epoch: a circular roll of the
    # sample data does not change when the timeseries begins.
    assert shifted_ts.epoch == ts.epoch


def test_timeseries_cyclic_time_shift_preserves_epoch():
    ts = TimeSeries(np.array([1.0, 2.0, 3.0, 4.0]), epoch=1234.5, delta_t=0.2)
    shifted_ts = ts.cyclic_time_shift(0.6)  # Shift by 3 samples

    assert np.array_equal(shifted_ts.data, np.array([2.0, 3.0, 4.0, 1.0]))
    # Epoch must be unchanged by the cyclic shift.
    assert shifted_ts.epoch == 1234.5
    assert not isinstance(shifted_ts.epoch, np.floating)
    assert shifted_ts.delta_t == 0.2
    # Sample times still begin at the original epoch.
    assert shifted_ts.sample_times[0] == 1234.5


def test_timeseries_real():
    data = np.array([1.0 + 1j, 2.0 + 2j, 3.0 + 3j])
    ts = TimeSeries(data, 0.0, 1.0)
    real_ts = ts.real()
    assert np.array_equal(real_ts.data, np.array([1.0, 2.0, 3.0]))
    assert isinstance(real_ts, TimeSeries)


class TestTimeSeries(TestSeries):
    """Runs all base Series tests against a TimeSeries."""

    def make_series(self, data):
        return TimeSeries(data, epoch=0.0, delta_t=1.0)
