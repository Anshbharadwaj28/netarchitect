import math
from typing import List, Tuple
from core.exceptions import SubnetExhaustionError
from core.models import SubnetRequest, SubnetAllocation


class VLSMEngine:
    @staticmethod
    def _ip_to_int(ip_str: str) -> int:
        octets = [int(o) for o in ip_str.split(".")]
        return (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]

    @staticmethod
    def _int_to_ip(ip_int: int) -> str:
        return f"{(ip_int >> 24) & 255}.{(ip_int >> 16) & 255}.{(ip_int >> 8) & 255}.{ip_int & 255}"

    @classmethod
    def parse_cidr(cls, cidr_str: str) -> Tuple[int, int]:
        ip_part, prefix_part = cidr_str.strip().split("/")
        prefix = int(prefix_part)
        if not (0 <= prefix <= 30):
            raise ValueError(f"Unsupported root prefix /{prefix}. Must be between /0 and /30.")
        return cls._ip_to_int(ip_part), prefix

    @classmethod
    def calculate_vlsm(cls, root_cidr: str, requests: List[SubnetRequest]) -> List[SubnetAllocation]:
        root_ip_int, root_prefix = cls.parse_cidr(root_cidr)
        root_capacity = 1 << (32 - root_prefix)
        root_netmask_int = ((1 << 32) - 1) ^ ((1 << (32 - root_prefix)) - 1)
        root_base_network = root_ip_int & root_netmask_int

        # Sort requested subnets in descending order of needed host capacity
        sorted_requests = sorted(requests, key=lambda req: req.hosts_needed, reverse=True)

        current_base = root_base_network
        allocations: List[SubnetAllocation] = []

        for req in sorted_requests:
            if req.hosts_needed <= 0:
                raise ValueError(f"Subnet '{req.name}' requests invalid host count: {req.hosts_needed}")

            needed_size = req.hosts_needed + 2  # Network ID + Directed Broadcast
            # Compute power-of-two host bits: 2^(host_bits) >= needed_size
            host_bits = max(2, math.ceil(math.log2(needed_size)))
            prefix_len = 32 - host_bits
            block_size = 1 << host_bits

            # Align current_base to block_size boundary
            remainder = current_base % block_size
            if remainder != 0:
                current_base += (block_size - remainder)

            # Check if this allocation overruns the root CIDR block capacity
            if (current_base + block_size) > (root_base_network + root_capacity):
                raise SubnetExhaustionError(
                    f"Subnet exhaustion: Cannot allocate /{prefix_len} ({block_size} IPs) for '{req.name}'. "
                    f"Exceeds available capacity of root CIDR {root_cidr} ({root_capacity} total IPs)."
                )

            mask_int = ((1 << 32) - 1) ^ (block_size - 1)
            wildcard_int = block_size - 1
            network_int = current_base
            gateway_int = current_base + 1
            broadcast_int = current_base + block_size - 1

            allocations.append(
                SubnetAllocation(
                    name=req.name,
                    vlan_id=req.vlan_id,
                    hosts_requested=req.hosts_needed,
                    hosts_usable=block_size - 2,
                    prefix_length=prefix_len,
                    network_address=cls._int_to_ip(network_int),
                    subnet_mask=cls._int_to_ip(mask_int),
                    wildcard_mask=cls._int_to_ip(wildcard_int),
                    default_gateway=cls._int_to_ip(gateway_int),
                    broadcast_address=cls._int_to_ip(broadcast_int),
                    traffic_class=req.traffic_class
                )
            )

            current_base += block_size

        return allocations