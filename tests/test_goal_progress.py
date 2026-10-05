import pytest

from src.nutrition import goal_progress


def test_below_goal_returns_percentage():
    assert goal_progress(1250, 2500) == pytest.approx(50)


def test_zero_intake_returns_zero():
    assert goal_progress(0, 2500) == 0


def test_exact_goal_returns_100():
    assert goal_progress(2500, 2500) == pytest.approx(100)


def test_over_goal_is_capped_at_100():
    # Progress bars break above 100%, so the value must be capped
    assert goal_progress(4000, 2500) == pytest.approx(100)
    assert goal_progress(10000, 1) == pytest.approx(100)


@pytest.mark.parametrize("goal", [0, -100])
def test_non_positive_goal_returns_zero(goal):
    assert goal_progress(1500, goal) == 0


def test_fractional_values():
    assert goal_progress(80.5, 150) == pytest.approx(80.5 / 150 * 100)
