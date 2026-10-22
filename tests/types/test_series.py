import numpy as np
import pytest

from gwaith.types import Series


class TestSeries:
    """Base test class for Series and its subclasses.

    Subclasses override ``make_series`` to instantiate their specific type,
    which causes every test in this class to run against that type.
    """

    def make_series(self, data):
        """Factory method – override in subclasses."""
        return Series(data)

    # ------------------------------------------------------------------
    # Construction / basic protocol
    # ------------------------------------------------------------------

    def test_init(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        s = self.make_series(data)
        assert np.array_equal(s.data, data)

    def test_len(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        s = self.make_series(data)
        assert len(s) == 4

    def test_getitem_int(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        s = self.make_series(data)
        assert s[0] == 1.0

    def test_getitem_slice(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        s = self.make_series(data)
        result = s[1:3]
        assert isinstance(result, type(s))
        assert np.array_equal(result.data, np.array([2.0, 3.0]))

    @pytest.mark.parametrize("key", [slice(-3, -1), slice(None, None, 2), slice(2, 2)])
    def test_slice_boundaries(self, key):
        data = np.arange(6.0)
        series = self.make_series(data)
        result = series[key]
        assert type(result) is type(series)
        np.testing.assert_array_equal(result.data, data[key])

    def test_negative_integer_returns_scalar(self):
        series = self.make_series(np.arange(4.0))
        assert np.isscalar(series[-1])
        assert series[-1] == 3.0

    def test_setitem_int(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        s = self.make_series(data)
        s[0] = 10.0
        assert s[0] == 10.0

    def test_setitem_slice(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        s = self.make_series(data)
        s[1:3] = np.array([20.0, 30.0])
        assert np.array_equal(s.data, np.array([1.0, 20.0, 30.0, 4.0]))

    # ------------------------------------------------------------------
    # Arithmetic
    # ------------------------------------------------------------------

    def test_add(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        s1 = self.make_series(data.copy())
        s2 = self.make_series(data.copy())
        s_sum = s1 + s2
        assert isinstance(s_sum, type(s1))
        assert np.array_equal(s_sum.data, data * 2)

    def test_mul_scalar(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        s = self.make_series(data)
        s_mul = s * 2.0
        assert isinstance(s_mul, type(s))
        assert np.array_equal(s_mul.data, data * 2.0)

    # ------------------------------------------------------------------
    # Element-wise transforms
    # ------------------------------------------------------------------

    def test_real(self):
        data = np.array([1.0 + 1j, 2.0 + 2j, 3.0 + 3j])
        s = self.make_series(data)
        real_s = s.real()
        assert isinstance(real_s, type(s))
        assert np.array_equal(real_s.data, np.array([1.0, 2.0, 3.0]))

    # ------------------------------------------------------------------
    # Built-in function support (abs, max, min, sum)
    # ------------------------------------------------------------------

    def test_abs_builtin(self):
        data = np.array([-1.0, -2.0, 3.0, -4.0])
        s = self.make_series(data)
        result = abs(s)
        assert isinstance(result, type(s))
        assert np.array_equal(result.data, np.abs(data))

    def test_max_builtin(self):
        data = np.array([1.0, 5.0, 3.0, 2.0])
        s = self.make_series(data)
        assert max(s) == 5.0

    def test_min_builtin(self):
        data = np.array([1.0, 5.0, -3.0, 2.0])
        s = self.make_series(data)
        assert min(s) == -3.0

    def test_sum_builtin(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        s = self.make_series(data)
        assert sum(s) == pytest.approx(10.0)

    # ------------------------------------------------------------------
    # Method form (series.abs(), series.max(), etc.)
    # ------------------------------------------------------------------

    def test_abs_method(self):
        data = np.array([-1.0, -2.0, 3.0, -4.0])
        s = self.make_series(data)
        result = s.abs()
        assert isinstance(result, type(s))
        assert np.array_equal(result.data, np.abs(data))

    def test_max_method(self):
        data = np.array([1.0, 5.0, 3.0, 2.0])
        s = self.make_series(data)
        assert s.max() == 5.0

    def test_min_method(self):
        data = np.array([1.0, 5.0, -3.0, 2.0])
        s = self.make_series(data)
        assert s.min() == -3.0

    def test_sum_method(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        s = self.make_series(data)
        assert s.sum() == pytest.approx(10.0)
