import os
import sys
import json
import argparse
from netarchitect.core.models import (
    SubnetRequest,
    PhysicalLinkRequest,
    NetworkArchitecturePlan
)
from netarchitect.core.vlsm_engine import VLSMEngine
from netarchitect.core.media_engine import MediaEngine
from netarchitect.core.routing_engine import RoutingEngine
from netarchitect.core.exceptions import NetArchitectException
from netarchitect.generators.cisco_ios import CiscoIOSGenerator
from netarchitect.generators.report_engine import ReportEngine


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="NetArchitect",
        description="Autonomous Enterprise Network Architecture & Cisco IOS Generator (Course: CIC-307)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--preset",
        type=str,
        choices=["campus", "metro", "wan"],
        help="Load an official preset scenario: 'campus', 'metro', or 'wan'"
    )
    group.add_argument(
        "--input",
        type=str,
        help="Path to custom JSON network parameter specification"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="exports",
        help="Target directory for generated Cisco .cfg and Markdown report files"
    )
    return parser.parse_args()


def load_config_data(preset: str, input_path: str) -> dict:
    if preset:
        preset_map = {
            "campus": os.path.join("config", "preset_campus.json"),
            "metro": os.path.join("config", "preset_metro.json"),
            "wan": os.path.join("config", "preset_wan.json")
        }
        target_file = preset_map[preset]
    else:
        target_file = input_path

    if not os.path.exists(target_file):
        raise FileNotFoundError(f"Configuration file not found: {target_file}")

    with open(target_file, "r", encoding="utf-8") as f:
        return json.load(f)


def build_architecture(data: dict) -> NetworkArchitecturePlan:
    subnet_requests = [
        SubnetRequest(
            name=s["name"],
            hosts_needed=s["hosts_needed"],
            vlan_id=s["vlan_id"],
            traffic_class=s.get("traffic_class", "standard")
        )
        for s in data["subnets"]
    ]

    link_requests = [
        PhysicalLinkRequest(
            source=l["source"],
            destination=l["destination"],
            distance_meters=float(l["distance_meters"]),
            required_bandwidth_gbps=float(l.get("required_bandwidth_gbps", 10.0)),
            medium_override=l.get("medium_override")
        )
        for l in data["links"]
    ]

    allocations = VLSMEngine.calculate_vlsm(data["root_cidr"], subnet_requests)
    media_recs = [MediaEngine.evaluate_link(link) for link in link_requests]
    routing_policy = RoutingEngine.determine_policy(
        allocations=allocations,
        is_multi_site=data.get("is_multi_site", False),
        as_number=data.get("autonomous_system", 65000)
    )

    return NetworkArchitecturePlan(
        project_name=data.get("project_name", "Enterprise Plan"),
        profile_type=data.get("profile_type", "Custom Infrastructure"),
        root_cidr=data["root_cidr"],
        autonomous_system=data.get("autonomous_system", 65000),
        allocations=allocations,
        media_recommendations=media_recs,
        routing_policy=routing_policy
    )


def main():
    args = parse_arguments()

    try:
        raw_config = load_config_data(args.preset, args.input)
        plan = build_architecture(raw_config)

        report_md = ReportEngine.generate_markdown(plan)
        l2_cfg = CiscoIOSGenerator.generate_l2_access(plan)
        l3_cfg = CiscoIOSGenerator.generate_l3_core(plan)

        os.makedirs(args.output_dir, exist_ok=True)
        slug = plan.profile_type.lower().replace(" ", "_")

        report_file = os.path.join(args.output_dir, f"{slug}_design_report.md")
        l2_file = os.path.join(args.output_dir, f"{slug}_sw_access.cfg")
        l3_file = os.path.join(args.output_dir, f"{slug}_core_router.cfg")

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_md)
        with open(l2_file, "w", encoding="utf-8") as f:
            f.write(l2_cfg)
        with open(l3_file, "w", encoding="utf-8") as f:
            f.write(l3_cfg)

        print("\n=== NetArchitect Engine Execution Successful ===")
        print(f"Profile Ingested:       {plan.profile_type}")
        print(f"Subnets Allocated:      {len(plan.allocations)} non-overlapping CIDR blocks")
        print(f"Physical Media Solved:  {len(plan.media_recommendations)} backbone links")
        print(f"Routing Model Selected: {plan.routing_policy.protocol}")
        print("-" * 50)
        print(f"Exported Design Report: {report_file}")
        print(f"Exported L2 Access CFG: {l2_file}")
        print(f"Exported L3 Core CFG:   {l3_file}\n")

    except NetArchitectException as nae:
        print(f"\n[ENGINE FAILURE] Architectural Policy Violation: {str(nae)}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        print(f"\n[SYSTEM ERROR] Runtime Exception: {str(exc)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()