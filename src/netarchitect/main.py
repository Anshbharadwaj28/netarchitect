"""Command-line entry point for NetArchitect."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from netarchitect.core.models import SubnetRequest, PhysicalLinkRequest, NetworkArchitecturePlan
from netarchitect.core.vlsm_engine import VLSMEngine
from netarchitect.core.media_engine import MediaEngine
from netarchitect.core.routing_engine import RoutingEngine
from netarchitect.core.topology_engine import TopologyEngine
from netarchitect.core.params import load_json, ConfigurationError
from netarchitect.core.exceptions import NetArchitectException
from netarchitect.generators.cisco_ios import CiscoIOSGenerator
from netarchitect.generators.report_engine import ReportEngine
from netarchitect.core.acl_engine import generate_acl_config

PRESET_FILES = {
    "campus": "preset_campus.json",
    "metro": "preset_metro.json",
    "wan": "preset_wan.json",
}


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="NetArchitect", description="Enterprise network planning and Cisco IOS baseline generator (CIC-307).")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--preset", choices=PRESET_FILES, help="Load campus, metro, or wan preset.")
    source.add_argument("--input", help="Path to a custom JSON network specification.")
    parser.add_argument("--output-dir", default="exports", help="Directory for generated reports and configurations.")
    return parser.parse_args(argv)


def load_config_data(preset: str | None, input_path: str | None) -> dict:
    if preset:
        repository_config = Path(__file__).resolve().parents[2] / "config" / PRESET_FILES[preset]
        packaged_config = Path(__file__).resolve().parent / "presets" / PRESET_FILES[preset]
        config_path = repository_config if repository_config.is_file() else packaged_config
    else:
        config_path = Path(input_path).expanduser()
    return load_json(config_path)


def build_architecture(data: dict) -> NetworkArchitecturePlan:
    subnet_requests = [SubnetRequest(s["name"], s["hosts_needed"], s["vlan_id"], s.get("traffic_class", "standard")) for s in data["subnets"]]
    link_requests = [PhysicalLinkRequest(l["source"], l["destination"], float(l["distance_meters"]), float(l.get("required_bandwidth_gbps", 10.0)), l.get("medium_override")) for l in data["links"]]
    allocations = VLSMEngine.calculate_vlsm(data["root_cidr"], subnet_requests)
    media_recs = [MediaEngine.evaluate_link(link) for link in link_requests]
    as_number = data.get("autonomous_system", 65000)
    routing_policy = RoutingEngine.determine_policy(allocations, data.get("is_multi_site", False), as_number)
    endpoint_count = data.get("endpoints", sum(s.hosts_needed for s in subnet_requests))
    site_count = data.get("site_count", 2 if data.get("is_multi_site", False) else 1)
    topology = TopologyEngine.recommend(endpoint_count, site_count, data.get("dual_homed", False))
    return NetworkArchitecturePlan(
        project_name=data.get("project_name", "Enterprise Plan"), profile_type=data.get("profile_type", "Custom Infrastructure"),
        root_cidr=data["root_cidr"], autonomous_system=as_number, allocations=allocations,
        media_recommendations=media_recs, routing_policy=routing_policy, topology_recommendation=topology
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    try:
        raw_config = load_config_data(args.preset, args.input)
        plan = build_architecture(raw_config)
        output_dir = Path(args.output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        slug = plan.profile_type.lower().replace(" ", "_")
        outputs = {
            output_dir / f"{slug}_design_report.md": ReportEngine.generate_markdown(plan),
            output_dir / f"{slug}_sw_access.cfg": CiscoIOSGenerator.generate_l2_access(plan),
            output_dir / f"{slug}_core_router.cfg": CiscoIOSGenerator.generate_l3_core(plan),
        }
        acl_policies = raw_config.get("acl_policies", [])
        if acl_policies:
            outputs[output_dir / f"{slug}_security_acl.cfg"] = generate_acl_config(plan.allocations, acl_policies)
        acl_policies = raw_config.get("acl_policies", [])
        if acl_policies:
            outputs[output_dir / f"{slug}_security_acl.cfg"] = generate_acl_config(plan.allocations, acl_policies)
        for path, content in outputs.items():
            path.write_text(content, encoding="utf-8")
        print(f"NetArchitect completed: {plan.profile_type}")
        print(f"Subnets: {len(plan.allocations)} | Links: {len(plan.media_recommendations)}")
        print(f"Topology: {plan.topology_recommendation.topology}")
        for path in outputs:
            print(f"Generated: {path}")
        return 0
    except (NetArchitectException, ConfigurationError, ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"NetArchitect error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
