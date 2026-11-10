"""Deterministic topology recommendations from network scale and site count."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TopologyRecommendation:
    topology: str
    justification: str


class TopologyEngine:
    @staticmethod
    def recommend(endpoint_count: int, site_count: int, dual_homed: bool = False) -> TopologyRecommendation:
        if isinstance(endpoint_count, bool) or not isinstance(endpoint_count, int) or endpoint_count <= 0:
            raise ValueError("endpoint_count must be a positive integer.")
        if isinstance(site_count, bool) or not isinstance(site_count, int) or site_count <= 0:
            raise ValueError("site_count must be a positive integer.")
        if not isinstance(dual_homed, bool):
            raise ValueError("dual_homed must be a boolean.")
        if site_count == 1 and endpoint_count <= 500:
            topology = "Collapsed Core (Two-Tier)"
            reason = "A single site with up to 500 endpoints can use a collapsed core/distribution layer to reduce cost and operational complexity."
        elif site_count == 1:
            topology = "Three-Tier Hierarchical Campus"
            reason = "A larger single-site network benefits from separate core, distribution, and access layers for scale and fault isolation."
        else:
            topology = "Hierarchical Multi-Site WAN"
            reason = f"{site_count} geographically distinct sites require routed site boundaries and a hierarchical WAN design."
        if dual_homed:
            reason += " Dual-homing is recommended for redundant uplinks and improved path availability."
        return TopologyRecommendation(topology, reason)
