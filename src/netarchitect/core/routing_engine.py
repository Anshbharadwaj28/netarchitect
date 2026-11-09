from typing import List
from core.models import SubnetAllocation, RoutingPolicyRecommendation


class RoutingEngine:
    @staticmethod
    def determine_policy(allocations: List[SubnetAllocation], is_multi_site: bool, as_number: int = 65000) -> RoutingPolicyRecommendation:
        num_subnets = len(allocations)

        if not is_multi_site and num_subnets < 50:
            return RoutingPolicyRecommendation(
                protocol="Single-Area OSPFv2 (RFC 2328)",
                topology_type="Collapsed Core / Campus Enterprise Backbone",
                primary_area="Area 0 (Backbone)",
                border_protocol=None,
                autonomous_system=as_number,
                engineering_justification=(
                    f"Topology scale ({num_subnets} subnets within a single autonomous campus) does not justify "
                    "the Link-State Database (LSDB) SPF computational overhead of ABR summarization boundaries. "
                    "Single-Area OSPF Area 0 guarantees microsecond Dijkstra convergence, simplifies zero-touch adjacencies, "
                    "and complies with RFC 2328 campus best practices."
                )
            )
        else:
            return RoutingPolicyRecommendation(
                protocol="Hierarchical Multi-Area OSPFv2 with Border eBGP (RFC 4271)",
                topology_type="Distributed Multi-Site / Hybrid Cloud Enterprise WAN",
                primary_area="Area 0 Core Backbone + Non-Zero Leaf Areas",
                border_protocol="eBGP Peering",
                autonomous_system=as_number,
                engineering_justification=(
                    f"Network spans {num_subnets} subnets across multi-site boundaries or hybrid-cloud interconnects. "
                    "Multi-Area OSPF confines Link-State Advertisements (Type 1 & 2 LSAs) to regional areas via ABR route summarization, "
                    "preventing remote link flapping from triggering core SPF recalculations. Border routers leverage eBGP (AS "
                    f"{as_number}) for strict policy-based path-vector isolation and cloud prefix exchange."
                )
            )