"""Tests for configuration loading and validation."""
import pytest
from src.config import AppConfig


def test_app_config_load():
    cfg = AppConfig.load_from_yaml()
    assert cfg.study_area_name == "Adyar, Chennai"
    assert cfg.bbox.south == 13.000
    assert cfg.bbox.north == 13.030
    assert cfg.bbox.west == 80.215
    assert cfg.bbox.east == 80.265
    assert cfg.thresholds.walking_safe_depth_m == 0.15
    assert cfg.thresholds.driving_safe_depth_m == 0.20
    assert "walking" in cfg.profiles
    assert "driving" in cfg.profiles
    assert cfg.profiles["walking"].ignore_oneway is True
    assert cfg.profiles["driving"].ignore_oneway is False
    assert len(cfg.default_shelters) >= 2
