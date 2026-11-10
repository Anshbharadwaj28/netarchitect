
"""Generate Cisco IOS extended ACLs from explicit VLAN-to-VLAN policies."""

import re
from typing import Any


def generate_acl_config(allocations, policies: list[dict[str, Any]]) -> str:
    if not policies:
        return "! No ACL policies supplied. No ACLs were generated.\n"

    by_vlan = {item.vlan_id: item for item in allocations}
    grouped: dict[int, list[dict[str, Any]]] = {}
    names: set[str] = set()

    for index, policy in enumerate(policies):
        name = policy.get("name", f"POLICY_{index + 1}")

        if not isinstance(name, str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_-]{0,27}", name
        ):
            raise ValueError(f"Invalid ACL policy name: {name!r}.")

        if name.upper() in names:
            raise ValueError(f"Duplicate ACL policy name: {name}.")

        names.add(name.upper())

        source_vlan = policy["source_vlan"]
        destination_vlan = policy["destination_vlan"]

        if source_vlan not in by_vlan or destination_vlan not in by_vlan:
            raise ValueError(
                f"ACL policy {name} references an unknown source or destination VLAN."
            )

        if source_vlan == destination_vlan:
            raise ValueError(
                f"ACL policy {name} cannot target its own source VLAN."
            )

        action = policy.get("action", "deny").lower()
        protocol = policy.get("protocol", "ip").lower()

        if action not in {"permit", "deny"} or protocol not in {
            "ip", "tcp", "udp", "icmp"
        }:
            raise ValueError(
                f"ACL policy {name} has an unsupported action or protocol."
            )

        port = policy.get("destination_port")

        if port is not None and (
            protocol not in {"tcp", "udp"}
            or isinstance(port, bool)
            or not isinstance(port, int)
            or not 1 <= port <= 65535
        ):
            raise ValueError(
                f"ACL policy {name}: destination_port requires tcp/udp "
                "and must be 1..65535."
            )

        grouped.setdefault(source_vlan, []).append({
            **policy,
            "name": name,
            "action": action,
            "protocol": protocol,
            "destination_port": port
        })

    lines = [
        "! NetArchitect generated extended ACLs",
        "! Review security policy before deployment",
        "!"
    ]

    for source_vlan, rules in sorted(grouped.items()):
        acl_name = f"NA-VLAN{source_vlan}-IN"

        lines.append(f"ip access-list extended {acl_name}")

        for rule in rules:
            destination = by_vlan[rule["destination_vlan"]]

            lines.append(
                f" remark {rule['name']}: VLAN {source_vlan} "
                f"to VLAN {rule['destination_vlan']}"
            )

            command = (
                f" {rule['action']} {rule['protocol']} any "
                f"{destination.network_address} "
                f"{destination.wildcard_mask}"
            )

            if rule["destination_port"] is not None:
                command += f" eq {rule['destination_port']}"

            lines.append(command)

        lines.extend([
            " permit ip any any",
            "!",
            f"interface Vlan{source_vlan}",
            f" ip access-group {acl_name} in",
            "!"
        ])

    lines.append("end")

    # Join lines using actual newline characters.
    return "\n".join(lines) + "\n"
