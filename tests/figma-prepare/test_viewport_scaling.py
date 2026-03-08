"""Tests for viewport-relative threshold scaling (Proposal 6)."""
import pytest
from figma_utils.constants import compute_viewport_scale, scaled_threshold


class TestComputeViewportScale:
    def test_base_viewport(self):
        result = compute_viewport_scale(1440)
        assert result['w_scale'] == pytest.approx(1.0)

    def test_half_width(self):
        result = compute_viewport_scale(720)
        assert result['w_scale'] == pytest.approx(0.5)

    def test_double_width(self):
        result = compute_viewport_scale(2880)
        assert result['w_scale'] == pytest.approx(2.0)

    def test_mobile(self):
        result = compute_viewport_scale(375)
        assert result['w_scale'] == pytest.approx(375 / 1440)

    def test_with_height(self):
        result = compute_viewport_scale(1440, 8500)
        assert result['h_scale'] == pytest.approx(1.0)
        assert result['scale'] == pytest.approx(1.0)

    def test_zero_width(self):
        result = compute_viewport_scale(0)
        assert result['w_scale'] == 0.0

    def test_no_height_uses_w_scale(self):
        """When page_height is 0, h_scale should fallback to w_scale."""
        result = compute_viewport_scale(720, 0)
        assert result['h_scale'] == pytest.approx(0.5)
        assert result['scale'] == pytest.approx(0.5)

    def test_geometric_mean(self):
        """Scale should be geometric mean of w_scale and h_scale."""
        result = compute_viewport_scale(2880, 8500)
        # w_scale=2.0, h_scale=1.0, geometric mean = sqrt(2.0 * 1.0)
        assert result['scale'] == pytest.approx(2.0 ** 0.5)


class TestScaledThreshold:
    def test_identity(self):
        assert scaled_threshold(120, 1.0) == 120

    def test_half_scale(self):
        assert scaled_threshold(120, 0.5) == 60

    def test_min_value(self):
        assert scaled_threshold(120, 0.1, min_value=50) == 50

    def test_max_value(self):
        assert scaled_threshold(120, 3.0, max_value=200) == 200

    def test_both_bounds(self):
        assert scaled_threshold(120, 0.1, min_value=50, max_value=200) == 50
        assert scaled_threshold(120, 3.0, min_value=50, max_value=200) == 200

    def test_truncates_to_int(self):
        """Result should always be an integer."""
        result = scaled_threshold(100, 0.33)
        assert isinstance(result, int)
        assert result == 33

    def test_zero_scale(self):
        assert scaled_threshold(120, 0.0) == 0

    def test_zero_scale_with_min(self):
        assert scaled_threshold(120, 0.0, min_value=10) == 10
