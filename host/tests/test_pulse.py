"""Test tạo chuỗi xung bậc thang/vuông."""

import pytest

from robot_host.pulse import analyze_step, build_plan


def test_step_plan_alternates_on_off_equal_duration():
    plan = build_plan(100.0, 500.0, 9999.0, 2, False, 333.0)
    assert plan == [
        (100.0, 0.5),
        (0.0, 0.5),
        (100.0, 0.5),
        (0.0, 0.5),
    ]


def test_square_plan_uses_period_minus_width_as_off_time():
    plan = build_plan(-80.0, 200.0, 1000.0, 1, True, 333.0)
    assert plan == [(-80.0, 0.2), (0.0, 0.8)]


def test_plan_rejects_bad_period():
    with pytest.raises(ValueError):
        build_plan(100.0, 500.0, 500.0, 1, True, 333.0)


@pytest.mark.parametrize(
    "amplitude,width,count",
    [(0.0, 500.0, 1), (400.0, 500.0, 1), (100.0, 0.0, 1), (100.0, 500.0, 0)],
)
def test_plan_rejects_invalid_inputs(amplitude, width, count):
    with pytest.raises(ValueError):
        build_plan(amplitude, width, 1000.0, count, True, 333.0)


def test_plan_truncates_float_count():
    plan = build_plan(50.0, 100.0, 200.0, 3.9, True, 333.0)
    assert len(plan) == 6


def test_analyze_step_positive_target():
    samples = [
        (0.00, 0.0),
        (0.05, 40.0),
        (0.10, 92.0),
        (0.20, 110.0),
        (0.30, 101.0),
        (0.40, 100.2),
        (0.50, 100.1),
    ]
    metrics = analyze_step(samples, 100.0, 0.5)
    assert metrics["sample_count"] == 7
    assert metrics["rise_time_ms"] == pytest.approx(100.0)
    assert metrics["overshoot_pct"] == pytest.approx(10.0)
    assert metrics["settling_time_ms"] == pytest.approx(300.0)
    assert metrics["steady_error_rpm"] == pytest.approx(0.15)
    assert metrics["peak_rpm"] == pytest.approx(110.0)


def test_analyze_step_negative_target():
    samples = [(0.0, 0.0), (0.1, -95.0), (0.2, -80.0), (0.3, -79.5)]
    metrics = analyze_step(samples, -80.0, 0.3)
    assert metrics["rise_time_ms"] == pytest.approx(100.0)
    assert metrics["overshoot_pct"] == pytest.approx((95.0 - 80.0) / 80.0 * 100.0)
    assert metrics["steady_error_rpm"] == pytest.approx(0.5)
    assert metrics["peak_rpm"] == pytest.approx(-95.0)


def test_analyze_step_needs_samples():
    assert analyze_step([(0.0, 0.0)], 100.0, 0.5) is None
    assert analyze_step([(0.0, 0.0), (0.1, 1.0), (0.2, 2.0)], 0.0, 0.5) is None
