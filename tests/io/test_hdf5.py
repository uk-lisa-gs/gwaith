import numpy as np
import pytest
from gwaith.types import TimeSeries, FrequencySeries


def test_timeseries_save_and_load(tmp_path):
    data = np.array([1.0, 2.0, 3.0])
    epoch = 100.0
    delta_t = 0.1
    ts_orig = TimeSeries(data, epoch, delta_t)

    filepath = tmp_path / "test_ts.h5"
    ts_orig.save(str(filepath)) # Use default dataset_name

    ts_loaded = TimeSeries.load(str(filepath)) # Load with default dataset_name
    assert np.array_equal(ts_loaded.data, data)
    assert ts_loaded.epoch == epoch
    assert ts_loaded.delta_t == delta_t
    
    # Test with default dataset_name
    filepath_default = tmp_path / "test_ts_default.h5"
    ts_orig.save(str(filepath_default))
    ts_loaded_default = TimeSeries.load(str(filepath_default))
    assert np.array_equal(ts_loaded_default.data, data)
    assert ts_loaded_default.epoch == epoch
    assert ts_loaded_default.delta_t == delta_t

    # Test with a different dataset_name
    ts_orig.save(str(filepath), dataset_name="custom_data")
    ts_loaded = TimeSeries.load(str(filepath), dataset_name="custom_data")
    assert np.array_equal(ts_loaded.data, data)
    assert ts_loaded.epoch == epoch
    assert ts_loaded.delta_t == delta_t


def test_frequencyseries_save_and_load(tmp_path):
    data = np.array([1.0 + 1j, 2.0 + 2j])
    f0 = 0.0
    delta_f = 0.5
    epoch = 100.0
    fs_orig = FrequencySeries(data, delta_f=delta_f, f0=f0, epoch=epoch)

    # Test with explicit dataset_name
    filepath = tmp_path / "test_fs.h5"
    fs_orig.save(str(filepath), dataset_name="test_psd")

    fs_loaded = FrequencySeries.load(str(filepath), dataset_name="test_psd")
    assert np.array_equal(fs_loaded.data, data)
    assert fs_loaded.f0 == f0
    assert fs_loaded.delta_f == delta_f
    assert fs_loaded.epoch == epoch

    # Test with default dataset_name
    filepath_default = tmp_path / "test_fs_default.h5"
    fs_orig.save(str(filepath_default))
    fs_loaded_default = FrequencySeries.load(str(filepath_default))
    assert np.array_equal(fs_loaded_default.data, data)
    assert fs_loaded_default.f0 == f0
    assert fs_loaded_default.delta_f == delta_f
    assert fs_loaded_default.epoch == epoch

    # Without epoch
    fs_orig_no_epoch = FrequencySeries(data, delta_f=delta_f, f0=f0)
    filepath_no_epoch = tmp_path / "test_fs_no_epoch.h5"
    fs_orig_no_epoch.save(str(filepath_no_epoch))
    fs_loaded_no_epoch = FrequencySeries.load(str(filepath_no_epoch))
    assert np.array_equal(fs_loaded_no_epoch.data, data)
    assert fs_loaded_no_epoch.f0 == f0
    assert not hasattr(fs_loaded_no_epoch, 'epoch')