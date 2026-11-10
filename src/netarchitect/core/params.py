"""Configuration loading and validation for preset and custom JSON inputs."""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any
from .models import SubnetRequest
from .vlsm_engine import VLSMEngine
from .exceptions import NetArchitectException


class ConfigurationError(ValueError):
    """Raised when a network configuration is incomplete or invalid."""


def validate_config(data: Any) -> dict:
    if not isinstance(data, dict):
        raise ConfigurationError("Configuration root must be a JSON object.")
    required = {"root_cidr", "subnets", "links"}
    missing = required - data.keys()
    if missing:
        raise ConfigurationError(f"Missing required configuration keys: {', '.join(sorted(missing))}.")
    try:
        VLSMEngine.parse_cidr(data["root_cidr"])
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(str(exc)) from exc
    if not isinstance(data["subnets"], list) or not data["subnets"]:
        raise ConfigurationError("'subnets' must be a non-empty array.")
    for i, subnet in enumerate(data["subnets"]):
        if not isinstance(subnet, dict):
            raise ConfigurationError(f"subnets[{i}] must be an object.")
        for key in ("name", "hosts_needed", "vlan_id"):
            if key not in subnet:
                raise ConfigurationError(f"subnets[{i}] is missing '{key}'.")
        if not isinstance(subnet["name"], str) or not subnet["name"].strip():
            raise ConfigurationError(f"subnets[{i}].name must be a non-empty string.")
        if not isinstance(subnet["hosts_needed"], int) or isinstance(subnet["hosts_needed"], bool) or subnet["hosts_needed"] <= 0:
            raise ConfigurationError(f"subnets[{i}].hosts_needed must be a positive integer.")
        if not isinstance(subnet["vlan_id"], int) or isinstance(subnet["vlan_id"], bool) or not 1 <= subnet["vlan_id"] <= 4094:
            raise ConfigurationError(f"subnets[{i}].vlan_id must be between 1 and 4094.")
    if not isinstance(data["links"], list) or not data["links"]:
        raise ConfigurationError("'links' must be a non-empty array.")
    for i, link in enumerate(data["links"]):
        if not isinstance(link, dict) or not all(k in link for k in ("source", "destination", "distance_meters")):
            raise ConfigurationError(f"links[{i}] requires source, destination, and distance_meters.")
        if not isinstance(link["source"], str) or not link["source"].strip() or not isinstance(link["destination"], str) or not link["destination"].strip():
            raise ConfigurationError(f"links[{i}] source and destination must be non-empty strings.")
        distance = link["distance_meters"]
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or not math.isfinite(distance) or distance < 0:
            raise ConfigurationError(f"links[{i}].distance_meters must be a finite non-negative number.")
        bandwidth = link.get("required_bandwidth_gbps", 10.0)
        if isinstance(bandwidth, bool) or not isinstance(bandwidth, (int, float)) or not math.isfinite(bandwidth) or bandwidth <= 0:
            raise ConfigurationError(f"links[{i}].required_bandwidth_gbps must be a positive finite number.")
    # Reuse engine-level validation for VLAN uniqueness, names, and address-space fit.
    try:
        reqs = [SubnetRequest(s["name"], s["hosts_needed"], s["vlan_id"], s.get("traffic_class", "standard")) for s in data["subnets"]]
        VLSMEngine.calculate_vlsm(data["root_cidr"], reqs)
    except (ValueError, TypeError, NetArchitectException) as exc:
        raise ConfigurationError(str(exc)) from exc
    if "autonomous_system" in data and (not isinstance(data["autonomous_system"], int) or isinstance(data["autonomous_system"], bool) or not 1 <= data["autonomous_system"] <= 4294967295):
        raise ConfigurationError("autonomous_system must be an integer between 1 and 4294967295.")
    for key in ("endpoints", "site_count"):
        if key in data and (not isinstance(data[key], int) or isinstance(data[key], bool) or data[key] <= 0):
            raise ConfigurationError(f"{key} must be a positive integer.")
    if "is_multi_site" in data and not isinstance(data["is_multi_site"], bool):
        raise ConfigurationError("is_multi_site must be a boolean.")
    if "dual_homed" in data and not isinstance(data["dual_homed"], bool):
        raise ConfigurationError("dual_homed must be a boolean.")
    for key in ("project_name", "profile_type"):
        if key in data and (not isinstance(data[key], str) or not data[key].strip()):
            raise ConfigurationError(f"{key} must be a non-empty string.")
    acl_policies = data.get("acl_policies", [])
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
    acl_policies = data.get("acl_policies", [])
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


def load_json(path: str | Path) -> dict:
    file_path = Path(path).expanduser().resolve()
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise ConfigurationError(f"Cannot read configuration file {file_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Invalid JSON in {file_path}: {exc}") from exc
    return validate_config(data)
