import numpy as np
import pytest
from gwaith.types import TimeSeries, FrequencySeries


def test_frequencyseries_init():
    data = np.array([1.0 + 1j, 2.0 + 2j])
    f0 = 0.0
    delta_f = 0.5
    epoch = 100.0
    fs = FrequencySeries(data, delta_f=delta_f, f0=f0, epoch=epoch)

    assert np.array_equal(fs.data, data)
    assert np.array_equal(fs.frequencies, np.array([0.0, 0.5]))
    assert fs.epoch == epoch

def test_frequencyseries_init_default_f0():
    data = np.array([1.0 + 1j, 2.0 + 2j])
    delta_f = 0.5
    fs = FrequencySeries(data, delta_f=delta_f)
    assert fs.f0 == 0.0
    assert np.array_equal(fs.frequencies, np.array([0.0, 0.5]))
    assert not hasattr(fs, "epoch")

def test_frequencyseries_sample_frequencies():
    frequencies = np.array([0.0, 0.5, 1.0])
    f0 = frequencies[0]
    delta_f = frequencies[1] - frequencies[0]
    fs = FrequencySeries(np.array([1,2,3]), delta_f=delta_f, f0=f0)
    assert np.array_equal(fs.sample_frequencies, frequencies)

def test_frequencyseries_delta_f():
    frequencies = np.array([0.0, 0.5, 1.0])
    f0 = frequencies[0]
    delta_f = frequencies[1] - frequencies[0]
    fs = FrequencySeries(np.array([1,2,3]), delta_f=delta_f, f0=f0)
    assert fs.delta_f == 0.5

    # Test with single frequency bin
    # For a single frequency bin, delta_f is what was passed to the constructor.
    # If we want fs.frequencies to be [0.0], then f0=0.0 and delta_f can be 0.0.
    fs_single = FrequencySeries(np.array([1]), delta_f=0.0, f0=0.0)
    assert fs_single.delta_f == 0.0

def test_frequencyseries_len():
    data = np.array([1.0, 2.0, 3.0, 4.0])
    expected_frequencies = np.array([0.0, 0.1, 0.2, 0.3])
    f0 = expected_frequencies[0]
    delta_f = expected_frequencies[1] - expected_frequencies[0]
    fs = FrequencySeries(data, delta_f=delta_f, f0=f0)
    assert len(fs) == 4

def test_frequencyseries_getitem():
    data = np.array([1.0, 2.0, 3.0, 4.0])
    expected_frequencies = np.array([0.0, 0.1, 0.2, 0.3])
    f0 = expected_frequencies[0]
    delta_f = expected_frequencies[1] - expected_frequencies[0]
    fs = FrequencySeries(data, delta_f=delta_f, f0=f0)
    assert fs[0] == 1.0
    assert np.array_equal(fs[1:3], np.array([2.0, 3.0]))

def test_frequencyseries_setitem():
    data = np.array([1.0, 2.0, 3.0])
    expected_frequencies = np.array([0.0, 0.1, 0.2])
    f0 = expected_frequencies[0]
    delta_f = expected_frequencies[1] - expected_frequencies[0]
    fs = FrequencySeries(data, delta_f=delta_f, f0=f0)
    fs[0] = 10.0
    assert fs[0] == 10.0
    fs[1:3] = np.array([20.0, 30.0])
    assert np.array_equal(fs.data, np.array([10.0, 20.0, 30.0]))

def test_frequencyseries_pow():
    data = np.array([2.0, 3.0])
    expected_frequencies = np.array([0.0, 0.1])
    f0 = expected_frequencies[0]
    delta_f = expected_frequencies[1] - expected_frequencies[0]
    fs = FrequencySeries(data, delta_f=delta_f, f0=f0)
    fs_pow = fs**2
    assert np.array_equal(fs_pow.data, np.array([4.0, 9.0]))

def test_frequencyseries_to_timeseries():
    # Create a simple timeseries, convert to freq, then back to time
    data = np.array([0.0, 1.0, 0.0, -1.0, 0.0, 1.0, 0.0, -1.0]) # A simple sine wave
    ts_orig = TimeSeries(data, 0.0, 0.1)
    fs = ts_orig.to_frequencyseries()
    ts_new = fs.to_timeseries()

    # The inverse FFT might not perfectly recover the original due to floating point and truncation for odd length
    # Let's compare lengths and approximate values
    assert isinstance(ts_new, TimeSeries)
    assert len(ts_new.data) == len(ts_orig.data)
    assert ts_new.epoch == ts_orig.epoch
    assert ts_new.delta_t == ts_orig.delta_t
    assert np.allclose(ts_new.data, ts_orig.data, atol=1e-9)

def test_frequencyseries_cyclic_time_shift():
    data = np.array([1.0, 2.0, 3.0, 4.0]) + 0j
    frequencies = np.array([0.0, 0.25, 0.5, 0.75])
    f0 = frequencies[0]
    delta_f = frequencies[1] - frequencies[0]
    fs = FrequencySeries(data, delta_f=delta_f, f0=f0, epoch=0.0)
    
    seconds_to_shift = 1.0
    shifted_fs = fs.cyclic_time_shift(seconds_to_shift)
    
    expected_phase_shift = np.exp(2j * np.pi * fs.frequencies * seconds_to_shift)
    expected_data = data * expected_phase_shift
    
    assert np.allclose(shifted_fs.data, expected_data)
    assert shifted_fs.epoch == fs.epoch
    assert shifted_fs.delta_f == fs.delta_f

def test_frequencyseries_conj():
    data = np.array([1.0 + 1j, 2.0 + 2j])
    fs = FrequencySeries(data, delta_f=0.5)
    fs_conj = fs.conj()
    assert np.array_equal(fs_conj.data, np.array([1.0 - 1j, 2.0 - 2j]))

def test_frequencyseries_resize():
    data = np.array([1.0, 2.0, 3.0])
    f0 = 0.0
    delta_f = 0.1
    fs = FrequencySeries(data, delta_f=delta_f, f0=f0)
    fs.resize(5)
    assert len(fs.data) == 5
    assert len(fs.frequencies) == 5
    assert np.array_equal(fs.data, np.array([1.0, 2.0, 3.0, 0.0, 0.0]))
    assert np.allclose(fs.frequencies, np.array([0.0, 0.1, 0.2, 0.3, 0.4]))

def test_frequencyseries_astype():
    data = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    f0 = 0.0
    delta_f = 0.1
    fs = FrequencySeries(data, delta_f=delta_f, f0=f0)
    fs_astype = fs.astype(np.float64)
    assert fs_astype.dtype == np.float64
    assert np.array_equal(fs_astype.data, data.astype(np.float64))

def test_frequencyseries_abs():
    data = np.array([3.0 + 4j, -3.0 + 4j])
    fs = FrequencySeries(data, delta_f=0.1)
    fs_abs = fs.abs()
    assert np.array_equal(fs_abs.data, np.array([5.0, 5.0]))

def test_frequencyseries_max_sum_min():
    data = np.array([1.0, 5.0, 2.0, 8.0])
    fs = FrequencySeries(data, delta_f=0.1)
    assert fs.max() == 8.0
    assert fs.sum() == 16.0
    assert fs.min() == 1.0

def test_frequencyseries_mul_scalar():
    fs = FrequencySeries(np.array([1.0 + 1j, 2.0 + 2j]), delta_f=0.5)
    fs_mul = fs * 2.0
    assert np.array_equal(fs_mul.data, np.array([2.0 + 2j, 4.0 + 4j]))

def test_frequencyseries_mul_frequencyseries():
    fs1 = FrequencySeries(np.array([1.0 + 1j, 2.0 + 2j]), delta_f=0.5)
    fs2 = FrequencySeries(np.array([2.0 + 2j, 3.0 + 3j]), delta_f=0.5)
    fs_mul = fs1 * fs2
    assert np.array_equal(fs_mul.data, np.array([0.0 + 4j, 0.0 + 12j]))

def test_frequencyseries_div_scalar():
    fs = FrequencySeries(np.array([2.0 + 2j, 4.0 + 4j]), delta_f=0.5)
    fs_div = fs / 2.0
    assert np.array_equal(fs_div.data, np.array([1.0 + 1j, 2.0 + 2j]))

def test_frequencyseries_div_frequencyseries():
    fs1 = FrequencySeries(np.array([2.0 + 2j, 4.0 + 4j]), delta_f=0.5)
    fs2 = FrequencySeries(np.array([1.0 + 1j, 2.0 + 2j]), delta_f=0.5)
    fs_div = fs1 / fs2
    assert np.array_equal(fs_div.data, np.array([2.0, 2.0]))
