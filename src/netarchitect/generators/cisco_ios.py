from ..core.models import NetworkArchitecturePlan


class CiscoIOSGenerator:
    @staticmethod
    def generate_l2_access(plan: NetworkArchitecturePlan) -> str:
        lines = [
            "!",
            f"! NetArchitect L2 Access Switch Configuration: {plan.project_name}",
            f"! Generated automatically under RFC/IEEE reference constraints",
            "!",
            "hostname SW-ACCESS-01",
            "no ip routing",
            "spanning-tree mode rapid-pvst",
            "spanning-tree portfast default",
            "spanning-tree portfast bpduguard default",
            "!"
        ]

        # VLAN database declaration
        for sub in plan.allocations:
            lines.extend([
                f"vlan {sub.vlan_id}",
                f" name {sub.name[:32]}",
                "!"
            ])

        # Uplink 802.1Q trunking
        allowed_vlans = ",".join(str(sub.vlan_id) for sub in plan.allocations)
        lines.extend([
            "interface GigabitEthernet0/1",
            " description UPLINK-TO-DISTRIBUTION-CORE",
            " switchport trunk encapsulation dot1q",
            " switchport mode trunk",
            f" switchport trunk allowed vlan {allowed_vlans}",
            " switchport nonegotiate",
            " spanning-tree guard root",
            " no shutdown",
            "!"
        ])

        # Sample edge ports
        for idx, sub in enumerate(plan.allocations[:3], start=2):
            lines.extend([
                f"interface GigabitEthernet0/{idx}",
                f" description ACCESS-{sub.name}",
                " switchport mode access",
                f" switchport access vlan {sub.vlan_id}",
                " spanning-tree portfast",
                " no shutdown",
                "!"
            ])

        lines.append("end\n")
        return "\n".join(lines)

    @staticmethod
    def generate_l3_core(plan: NetworkArchitecturePlan) -> str:
        lines = [
            "!",
            f"! NetArchitect L3 Core / Distribution Router Configuration: {plan.project_name}",
            f"! Routing Protocol: {plan.routing_policy.protocol}",
            "!",
            "hostname CORE-ROUTER-01",
            "ip routing",
            "spanning-tree mode rapid-pvst",
            "!"
        ]

        # QoS Class-Maps and Policy-Maps
        lines.extend([
            "! Class Maps for Differentiated Services (DiffServ / RFC 4594)",
            "class-map match-any CLASS-VOICE",
            " match ip dscp ef",
            "class-map match-any CLASS-VIDEO",
            " match ip dscp af41 af42",
            "!",
            "policy-map WAN-EDGE-QOS",
            " class CLASS-VOICE",
            "  priority percent 30",
            " class CLASS-VIDEO",
            "  bandwidth percent 25",
            " class class-default",
            "  fair-queue",
            "!"
        ])

        # SVI Interfaces
        for sub in plan.allocations:
            lines.extend([
                f"interface Vlan{sub.vlan_id}",
                f" description GATEWAY-{sub.name}",
                f" ip address {sub.default_gateway} {sub.subnet_mask}",
                " no shutdown",
                "!"
            ])

        # Access Control Lists for Enterprise Hardening
        lines.extend([
            "ip access-list extended ACL-ISOLATE-MGMT",
            " permit udp any any eq bootps",
            " permit udp any any eq domain",
            " permit icmp any any",
            " deny ip 10.0.0.0 0.255.255.255 192.168.0.0 0.0.255.255",
            " permit ip any any",
            "!"
        ])

        # Routing Engine Statements
        ospf_pid = 1
        lines.extend([
            f"router ospf {ospf_pid}",
            " router-id 1.1.1.1",
            " passive-interface default"
        ])

        for sub in plan.allocations:
            area_id = "0"
            lines.append(f" no passive-interface Vlan{sub.vlan_id}")
            lines.append(f" network {sub.network_address} {sub.wildcard_mask} area {area_id}")

        if plan.routing_policy.border_protocol:
            lines.extend([
                "!",
                f"router bgp {plan.autonomous_system}",
                " bgp router-id 1.1.1.1",
                " bgp log-neighbor-changes",
                " neighbor 169.254.0.1 remote-as 64512",
                " neighbor 169.254.0.1 description CLOUD-DIRECT-CONNECT-EDGE",
                " neighbor 169.254.0.1 update-source Loopback0",
                " !",
                " address-family ipv4",
                f"  network {plan.allocations[0].network_address} mask {plan.allocations[0].subnet_mask}",
                "  neighbor 169.254.0.1 activate",
                " exit-address-family"
            ])

        lines.append("end\n")
        return "\n".join(lines)