$ErrorActionPreference = 'Stop'

if (-not (Test-Path '.\pyproject.toml')) {
    throw 'Run this script from the NetArchitect repository root (the folder containing pyproject.toml).'
}

$script = Join-Path $env:TEMP 'apply_cic307_acl_patch.py'
$source = @'
from pathlib import Path
ROOT = Path.cwd()
PKG = ROOT / 'src' / 'netarchitect'
if not (PKG / 'main.py').exists():
    raise SystemExit('Expected src/netarchitect/main.py. No changes made.')
(PKG / 'core' / 'acl_engine.py').write_text(r'''"""Generate Cisco IOS extended ACLs from explicit VLAN-to-VLAN policies."""
import re
from typing import Any

def generate_acl_config(allocations, policies: list[dict[str, Any]]) -> str:
    if not policies:
        return "! No ACL policies supplied. No ACLs were generated.\\n"
    by_vlan = {item.vlan_id: item for item in allocations}
    grouped: dict[int, list[dict[str, Any]]] = {}
    names: set[str] = set()
    for index, policy in enumerate(policies):
        name = policy.get("name", f"POLICY_{index + 1}")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,27}", name):
            raise ValueError(f"Invalid ACL policy name: {name!r}.")
        if name.upper() in names:
            raise ValueError(f"Duplicate ACL policy name: {name}.")
        names.add(name.upper())
        source_vlan, destination_vlan = policy["source_vlan"], policy["destination_vlan"]
        if source_vlan not in by_vlan or destination_vlan not in by_vlan:
            raise ValueError(f"ACL policy {name} references an unknown source or destination VLAN.")
        if source_vlan == destination_vlan:
            raise ValueError(f"ACL policy {name} cannot target its own source VLAN.")
        action, protocol = policy.get("action", "deny").lower(), policy.get("protocol", "ip").lower()
        if action not in {"permit", "deny"} or protocol not in {"ip", "tcp", "udp", "icmp"}:
            raise ValueError(f"ACL policy {name} has an unsupported action or protocol.")
        port = policy.get("destination_port")
        if port is not None and (protocol not in {"tcp", "udp"} or isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535):
            raise ValueError(f"ACL policy {name}: destination_port requires tcp/udp and must be 1..65535.")
        grouped.setdefault(source_vlan, []).append({**policy, "name": name, "action": action, "protocol": protocol, "destination_port": port})
    lines = ["! NetArchitect generated extended ACLs", "! Review security policy before deployment", "!"]
    for source_vlan, rules in sorted(grouped.items()):
        acl_name = f"NA-VLAN{source_vlan}-IN"
        lines.append(f"ip access-list extended {acl_name}")
        for rule in rules:
            destination = by_vlan[rule["destination_vlan"]]
            lines.append(f" remark {rule['name']}: VLAN {source_vlan} to VLAN {rule['destination_vlan']}")
            command = f" {rule['action']} {rule['protocol']} any {destination.network_address} {destination.wildcard_mask}"
            if rule["destination_port"] is not None:
                command += f" eq {rule['destination_port']}"
            lines.append(command)
        lines.extend([" permit ip any any", "!", f"interface Vlan{source_vlan}", f" ip access-group {acl_name} in", "!"])
    lines.append("end")
    return "\\n".join(lines) + "\\n"
''', encoding='utf-8')
params = PKG / 'core' / 'params.py'
s = params.read_text(encoding='utf-8')
needle = '    return data\n'
insert = '''    acl_policies = data.get("acl_policies", [])
    if not isinstance(acl_policies, list):
        raise ConfigurationError("acl_policies must be an array.")
    known_vlans = {subnet["vlan_id"] for subnet in data["subnets"]}
    policy_names = set()
    for i, policy in enumerate(acl_policies):
        if not isinstance(policy, dict) or not {"name", "source_vlan", "destination_vlan"}.issubset(policy):
            raise ConfigurationError(f"acl_policies[{i}] requires name, source_vlan, and destination_vlan.")
        name = policy["name"]
        if not isinstance(name, str) or not name.strip() or name.upper() in policy_names:
            raise ConfigurationError(f"acl_policies[{i}].name must be non-empty and unique.")
        policy_names.add(name.upper())
        for field in ("source_vlan", "destination_vlan"):
            vlan = policy[field]
            if not isinstance(vlan, int) or isinstance(vlan, bool) or vlan not in known_vlans:
                raise ConfigurationError(f"acl_policies[{i}].{field} must reference a configured VLAN.")
        if policy["source_vlan"] == policy["destination_vlan"]:
            raise ConfigurationError(f"acl_policies[{i}] source and destination VLANs must differ.")
        if policy.get("action", "deny") not in {"permit", "deny"}:
            raise ConfigurationError(f"acl_policies[{i}].action must be permit or deny.")
        if policy.get("protocol", "ip") not in {"ip", "tcp", "udp", "icmp"}:
            raise ConfigurationError(f"acl_policies[{i}].protocol must be ip, tcp, udp, or icmp.")
        port = policy.get("destination_port")
        if port is not None and (policy.get("protocol", "ip") not in {"tcp", "udp"} or isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535):
            raise ConfigurationError(f"acl_policies[{i}].destination_port requires tcp/udp and must be 1..65535.")
    return data
'''
if s.count(needle) != 1:
    raise SystemExit('Could not safely patch params.py. No further changes made.')
params.write_text(s.replace(needle, insert), encoding='utf-8')
main = PKG / 'main.py'
s = main.read_text(encoding='utf-8')
needle = 'from netarchitect.generators.report_engine import ReportEngine\n'
if needle not in s:
    raise SystemExit('Could not locate main.py imports. params.py and acl_engine.py were written; restore from git and retry.')
s = s.replace(needle, needle + 'from netarchitect.core.acl_engine import generate_acl_config\n')
needle = '        for path, content in outputs.items():\n'
insert = '''        acl_policies = raw_config.get("acl_policies", [])
        if acl_policies:
            outputs[output_dir / f"{slug}_security_acl.cfg"] = generate_acl_config(plan.allocations, acl_policies)
        for path, content in outputs.items():
'''
if s.count(needle) != 1:
    raise SystemExit('Could not locate main.py output loop.')
main.write_text(s.replace(needle, insert), encoding='utf-8')
tests = ROOT / 'tests' / 'test_acl_engine.py'
tests.write_text('''import pytest
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
''', encoding='utf-8')
print('ACL support added. Review changes, then run: python -m pytest -q')
'@
Set-Content -Path $script -Value $source -Encoding UTF8
python $script
if ($LASTEXITCODE -ne 0) { throw 'Patch failed. Check the Python error above.' }
Write-Host 'Patch applied. Run: python -m pytest -q' -ForegroundColor Green

# Align preset scale metadata with the assignment's three scenarios.
$profileScript = Join-Path $env:TEMP 'align_netarchitect_profiles.py'
$profileSource = @'
import json
from pathlib import Path
root = Path.cwd() / "config"
updates = {
    "preset_campus.json": {"endpoints": 1600, "site_count": 1, "dual_homed": False},
    "preset_metro.json": {"endpoints": 450, "site_count": 3, "dual_homed": True},
    "preset_wan.json": {"endpoints": 2000, "site_count": 4, "dual_homed": True},
}
for filename, fields in updates.items():
    path = root / filename
    if not path.exists():
        raise SystemExit(f"Missing expected preset: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(fields)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print("Preset endpoint/site/failover metadata aligned with CIC-307 scenario definitions.")
'@
Set-Content -Path $profileScript -Value $profileSource -Encoding UTF8
python $profileScript
if ($LASTEXITCODE -ne 0) { throw 'Preset metadata update failed.' }
Write-Host 'ACL support and preset metadata updates applied.' -ForegroundColor Green
Write-Host 'Run: python -m pytest -q' -ForegroundColor Cyan
