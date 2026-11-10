import pytest
from netarchitect.core.acl_engine import generate_acl_config
from netarchitect.core.models import SubnetRequest
from netarchitect.core.params import ConfigurationError, validate_config
from netarchitect.core.vlsm_engine import VLSMEngine

def allocations():
    return VLSMEngine.calculate_vlsm("10.10.0.0/24", [SubnetRequest("USERS", 50, 10), SubnetRequest("SERVERS", 20, 20)])

def test_acl_generation_and_svi_application():
    result = generate_acl_config(allocations(), [{"name": "BLOCK_USERS_TO_SERVERS", "source_vlan": 10, "destination_vlan": 20, "action": "deny", "protocol": "ip"}])
    assert "ip access-list extended NA-VLAN10-IN" in result
    assert "deny ip any" in result
    assert "permit ip any any" in result
    assert "ip access-group NA-VLAN10-IN in" in result

def test_acl_rejects_unknown_vlan():
    with pytest.raises(ValueError, match="unknown"):
        generate_acl_config(allocations(), [{"name": "BAD", "source_vlan": 10, "destination_vlan": 999}])

def test_config_validation_rejects_bad_acl_protocol():
    data = {"root_cidr": "10.0.0.0/24", "subnets": [{"name": "A", "hosts_needed": 20, "vlan_id": 10}, {"name": "B", "hosts_needed": 20, "vlan_id": 20}], "links": [{"source": "A", "destination": "B", "distance_meters": 10}], "acl_policies": [{"name": "BAD", "source_vlan": 10, "destination_vlan": 20, "protocol": "gre"}]}
    with pytest.raises(ConfigurationError, match="protocol"):
        validate_config(data)
