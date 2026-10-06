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


def test_timeseries_to_frequencyseries_scales_by_delta_t():
    # The forward transform is the integral (continuous) FT, i.e. scaled by
    # delta_t relative to the raw DFT sum. This keeps SNR on the correct
    # physical scale.
    data = np.array([0.0, 1.0, 0.0, -1.0, 0.0])
    delta_t = 0.25
    ts = TimeSeries(data, 0.0, delta_t)
    fs = ts.to_frequencyseries()

    # |H(f)| at the dominant bin must equal delta_t * |rfft| (the raw DFT).
    assert np.allclose(fs.data, delta_t * np.fft.rfft(data))


def test_timeseries_to_frequencyseries_snr_normalisation():
    # For a white-noise timeseries, the per-bin spectral power recovered by
    # to_frequencyseries must be sigma^2 * n * delta_t^2 (i.e. the DFT bin
    # variance sigma^2 * n scaled by the dt factor squared). Equivalently,
    # sum |H|^2 = sigma^2 * n^2 * delta_t^2 / 2, so dividing by that must give
    # a value that does NOT depend on either delta_t or n.
    rng = np.random.default_rng(42)

    def mean_power_ratio(delta_t: float, n: int) -> float:
        sigma = 1.0  # per-sample time-domain std dev, independent of delta_t
        total = 0.0
        for _ in range(30):
            h_i = rng.normal(0.0, sigma, size=n)
            fs_i = TimeSeries(h_i, 0.0, delta_t).to_frequencyseries()
            total += np.sum(np.abs(fs_i.data) ** 2) / (sigma**2 * n**2 * delta_t**2 / 2)
        return total / 30

    # The mean recovered power must be the same regardless of delta_t or n.
    # (The tolerance is generous because the estimate is an average over a
    # finite number of random draws.)
    for delta_t in (1.0, 0.5, 0.25):
        assert mean_power_ratio(delta_t, 4096) == pytest.approx(
            mean_power_ratio(1.0, 4096), rel=0.05
        )
    # Also check that changing n (at fixed delta_t) does not change the ratio.
    assert mean_power_ratio(0.5, 2048) == pytest.approx(
        mean_power_ratio(0.5, 8192), rel=0.05
    )


def test_timeseries_to_frequencyseries_roundtrip_preserves_amplitude():
    # A pure sine of amplitude A must come back with the same amplitude after
    # ts -> fs -> ts, regardless of delta_t. This guards the forward (dt) and
    # inverse (n*df) scalings against drifting out of sync.
    delta_t = 0.37
    n = 1024
    freq_bin = 5
    t = np.arange(n) * delta_t
    amp = 3.0
    data = amp * np.sin(2 * np.pi * freq_bin * t / (n * delta_t))
    ts = TimeSeries(data, 0.0, delta_t)

    ts_back = ts.to_frequencyseries().to_timeseries()
    assert np.allclose(ts_back.data, data, atol=1e-9)


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
