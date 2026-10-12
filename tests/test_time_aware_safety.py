"""Tests for time-aware flood depth safety evaluation."""
import pytest
from src.routing.safety import SafetyEvaluator
from src.scenarios.synthetic import SyntheticFloodScenario, DynamicFloodCurve


def test_static_edge_passability():
    scenario = SyntheticFloodScenario()
    # Edge 1->2 has static depth 0.18m
    scenario.set_static_edge_depth(1, 2, 0.18)

    evaluator = SafetyEvaluator(scenario)

    # For walking (limit 0.15m), 0.18m is unsafe / impassable
    passable_walk, depth_walk = evaluator.is_edge_passable(
        u=1, v=2, t_entry=0.0, duration=30.0, max_safe_depth=0.15
    )
    assert not passable_walk
    assert depth_walk == 0.18

    # For driving (limit 0.20m), 0.18m is safe / passable
    passable_drive, depth_drive = evaluator.is_edge_passable(
        u=1, v=2, t_entry=0.0, duration=30.0, max_safe_depth=0.20
    )
    assert passable_drive
    assert depth_drive == 0.18


def test_dynamic_edge_passability_time_window():
    scenario = SyntheticFloodScenario()
    # Edge 1->2 dry until t=100s, rises to 0.40m at t=300s
    scenario.set_dynamic_edge_curve(
        u=1,
        v=2,
        start_time_seconds=100.0,
        peak_time_seconds=300.0,
        peak_depth_m=0.40,
        base_depth_m=0.0,
    )

    evaluator = SafetyEvaluator(scenario)

    # Early arrival window [0, 60s]: water is 0.0m -> passable
    passable_early, depth_early = evaluator.is_edge_passable(
        u=1, v=2, t_entry=0.0, duration=60.0, max_safe_depth=0.15
    )
    assert passable_early
    assert depth_early == 0.0

    # Late arrival window [250, 280s]: depth is >0.30m -> impassable for both
    passable_late, depth_late = evaluator.is_edge_passable(
        u=1, v=2, t_entry=250.0, duration=30.0, max_safe_depth=0.20
    )
    assert not passable_late
    assert depth_late > 0.30

    # Traversal starting before flood (t=90s) but finishing when flood has risen (t=200s, depth=0.20m)
    # Walking threshold 0.15m: should fail because during traversal, peak depth reaches 0.20m
    passable_spanning, depth_spanning = evaluator.is_edge_passable(
        u=1, v=2, t_entry=90.0, duration=110.0, max_safe_depth=0.15
    )
    assert not passable_spanning
    assert depth_spanning == 0.20
