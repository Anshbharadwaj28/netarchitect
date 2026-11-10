import json
from pathlib import Path
import pytest
from netarchitect.core.params import validate_config, ConfigurationError
from netarchitect.core.topology_engine import TopologyEngine
from netarchitect.main import build_architecture, load_config_data

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("preset", ["campus", "metro", "wan"])
def test_all_presets_build_architecture(preset):
    data = load_config_data(preset, None)
    plan = build_architecture(data)
    assert plan.allocations
    assert plan.media_recommendations
    assert plan.topology_recommendation.topology


def test_config_rejects_missing_required_key():
    with pytest.raises(ConfigurationError, match="Missing required"):
        validate_config({"root_cidr": "10.0.0.0/24", "subnets": []})


def test_config_rejects_duplicate_vlan():
    data = {
        "root_cidr": "10.0.0.0/24",
        "subnets": [
            {"name": "A", "hosts_needed": 20, "vlan_id": 10},
            {"name": "B", "hosts_needed": 20, "vlan_id": 10},
        ],
        "links": [{"source": "A", "destination": "B", "distance_meters": 10}],
    }
    with pytest.raises(ConfigurationError, match="Duplicate VLAN"):
        validate_config(data)


def test_config_rejects_nan_distance():
    data = {
        "root_cidr": "10.0.0.0/24",
        "subnets": [{"name": "A", "hosts_needed": 20, "vlan_id": 10}],
        "links": [{"source": "A", "destination": "B", "distance_meters": float("nan")}],
    }
    with pytest.raises(ConfigurationError, match="finite non-negative"):
        validate_config(data)


def test_topology_selection_by_scale_and_resiliency():
    small = TopologyEngine.recommend(200, 1)
    large = TopologyEngine.recommend(1200, 1)
    multi = TopologyEngine.recommend(1200, 3, dual_homed=True)
    assert "Collapsed Core" in small.topology
    assert "Three-Tier" in large.topology
    assert "Multi-Site" in multi.topology
    assert "Dual-homing" in multi.justification


def test_topology_rejects_invalid_endpoint_count():
    with pytest.raises(ValueError):
        TopologyEngine.recommend(0, 1)


def test_cli_writes_report_and_both_device_configs(tmp_path):
    from netarchitect.main import main
    result = main(["--preset", "campus", "--output-dir", str(tmp_path)])
    assert result == 0
    assert (tmp_path / "campus_lan_design_report.md").is_file()
    assert (tmp_path / "campus_lan_sw_access.cfg").is_file()
    core = (tmp_path / "campus_lan_core_router.cfg").read_text(encoding="utf-8")
    assert "hostname CORE-SW1" in core
    assert "neighbor 169.254.0.1" not in core


def test_config_rejects_invalid_topology_metadata():
    data = {
        "root_cidr": "10.0.0.0/24",
        "subnets": [{"name": "A", "hosts_needed": 20, "vlan_id": 10}],
        "links": [{"source": "A", "destination": "B", "distance_meters": 10}],
        "site_count": 0,
    }
    with pytest.raises(ConfigurationError, match="site_count"):
        validate_config(data)
