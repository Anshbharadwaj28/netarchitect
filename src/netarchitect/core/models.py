from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .topology_engine import TopologyRecommendation


@dataclass(frozen=True)
class SubnetRequest:
    name: str
    hosts_needed: int
    vlan_id: int
    traffic_class: str = "standard"  # voice, video, standard, bulk


@dataclass(frozen=True)
class SubnetAllocation:
    name: str
    vlan_id: int
    hosts_requested: int
    hosts_usable: int
    prefix_length: int
    network_address: str
    subnet_mask: str
    wildcard_mask: str
    default_gateway: str
    broadcast_address: str
    traffic_class: str


@dataclass(frozen=True)
class PhysicalLinkRequest:
    source: str
    destination: str
    distance_meters: float
    required_bandwidth_gbps: float = 10.0
    medium_override: Optional[str] = None


@dataclass(frozen=True)
class PhysicalLinkRecommendation:
    source: str
    destination: str
    distance_meters: float
    recommended_media: str
    standard: str
    transceiver_type: str
    wavelength_nm: Optional[int]
    engineering_justification: str


@dataclass(frozen=True)
class RoutingPolicyRecommendation:
    protocol: str
    topology_type: str
    primary_area: str
    border_protocol: Optional[str]
    autonomous_system: int
    engineering_justification: str


@dataclass(frozen=True)
class NetworkArchitecturePlan:
    project_name: str
    profile_type: str
    root_cidr: str
    autonomous_system: int
    allocations: List[SubnetAllocation]
    media_recommendations: List[PhysicalLinkRecommendation]
    routing_policy: RoutingPolicyRecommendation
    topology_recommendation: Optional["TopologyRecommendation"] = None
