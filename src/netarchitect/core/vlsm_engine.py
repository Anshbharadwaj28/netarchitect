"""IPv4 VLSM allocation using integer arithmetic and strict CIDR validation."""
from __future__ import annotations

import ipaddress
from typing import List, Tuple

from .exceptions import SubnetExhaustionError
from .models import SubnetRequest, SubnetAllocation


class VLSMEngine:
    @staticmethod
    def _ip_to_int(ip_str: str) -> int:
        return int(ipaddress.IPv4Address(ip_str))

    @staticmethod
    def _int_to_ip(ip_int: int) -> str:
        return str(ipaddress.IPv4Address(ip_int))

    @classmethod
    def parse_cidr(cls, cidr_str: str) -> Tuple[int, int]:
        try:
            network = ipaddress.IPv4Network(cidr_str, strict=False)
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError) as exc:
            raise ValueError(f"Invalid IPv4 CIDR {cidr_str!r}: {exc}") from exc
        if network.prefixlen > 30:
            raise ValueError(f"Unsupported root prefix /{network.prefixlen}. Must be between /0 and /30.")
        return int(network.network_address), network.prefixlen

    @classmethod
    def calculate_vlsm(cls, root_cidr: str, requests: List[SubnetRequest]) -> List[SubnetAllocation]:
        root_ip_int, root_prefix = cls.parse_cidr(root_cidr)
        root_capacity = 1 << (32 - root_prefix)
        root_end = root_ip_int + root_capacity

        seen_names: set[str] = set()
        seen_vlans: set[int] = set()
        for req in requests:
            if not isinstance(req.hosts_needed, int) or isinstance(req.hosts_needed, bool) or req.hosts_needed <= 0:
                raise ValueError(f"Subnet '{req.name}' requests invalid host count: {req.hosts_needed!r}")
            if req.hosts_needed > (1 << 30) - 2:
                raise SubnetExhaustionError(f"Host request for '{req.name}' exceeds the maximum IPv4 subnet capacity.")
            if not isinstance(req.name, str) or not req.name.strip():
                raise ValueError(f"Subnet name must be a non-empty string: {req.name!r}.")
            if not isinstance(req.vlan_id, int) or isinstance(req.vlan_id, bool) or not 1 <= req.vlan_id <= 4094:
                raise ValueError(f"Subnet '{req.name}' has invalid VLAN ID {req.vlan_id!r}; expected 1..4094.")
            if req.vlan_id in seen_vlans:
                raise ValueError(f"Duplicate VLAN ID {req.vlan_id}.")
            if not req.name or req.name.strip() in seen_names:
                raise ValueError(f"Subnet names must be non-empty and unique: {req.name!r}.")
            seen_names.add(req.name.strip())
            seen_vlans.add(req.vlan_id)

        allocations: List[SubnetAllocation] = []
        current = root_ip_int
        for req in sorted(requests, key=lambda item: item.hosts_needed, reverse=True):
            block_size = 1 << max(2, (req.hosts_needed + 2 - 1).bit_length())
            prefix_len = 32 - (block_size.bit_length() - 1)
            current = ((current + block_size - 1) // block_size) * block_size
            if current + block_size > root_end:
                raise SubnetExhaustionError(
                    f"Subnet exhaustion: cannot allocate /{prefix_len} for '{req.name}' within {root_cidr}."
                )
            network = ipaddress.IPv4Network((current, prefix_len))
            wildcard = (1 << 32) - 1 - int(network.netmask)
            allocations.append(SubnetAllocation(
                name=req.name, vlan_id=req.vlan_id, hosts_requested=req.hosts_needed,
                hosts_usable=network.num_addresses - 2, prefix_length=prefix_len,
                network_address=str(network.network_address), subnet_mask=str(network.netmask),
                wildcard_mask=cls._int_to_ip(wildcard),
                default_gateway=str(network.network_address + 1),
                broadcast_address=str(network.broadcast_address), traffic_class=req.traffic_class
            ))
            current += block_size
        return allocations
