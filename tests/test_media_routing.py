import unittest
from netarchitect.core.models import PhysicalLinkRequest, SubnetAllocation
from netarchitect.core.media_engine import MediaEngine
from netarchitect.core.routing_engine import RoutingEngine
from netarchitect.core.exceptions import PhysicalDistanceViolationError


class TestMediaAndRouting(unittest.TestCase):
    def test_media_selection_boundaries(self):
        # Cat6a boundary: <= 100m
        l1 = PhysicalLinkRequest("SW1", "SW2", 95.0)
        r1 = MediaEngine.evaluate_link(l1)
        self.assertIn("Cat6a", r1.recommended_media)
        self.assertIn("802.3an", r1.standard)

        # OM4 MMF boundary: 101m - 400m
        l2 = PhysicalLinkRequest("SW1", "SW3", 250.0)
        r2 = MediaEngine.evaluate_link(l2)
        self.assertIn("OM4", r2.recommended_media)
        self.assertEqual(r2.wavelength_nm, 850)

        # OS2 SMF boundary: > 400m
        l3 = PhysicalLinkRequest("SW1", "DC1", 12000.0)
        r3 = MediaEngine.evaluate_link(l3)
        self.assertIn("OS2", r3.recommended_media)
        self.assertIn("SFP-10G-ER", r3.transceiver_type)

    def test_copper_distance_violation_error(self):
        violating_link = PhysicalLinkRequest(
            source="Campus-A",
            destination="Campus-B",
            distance_meters=140.0,
            medium_override="Cat6a"
        )
        with self.assertRaises(PhysicalDistanceViolationError) as cm:
            MediaEngine.evaluate_link(violating_link)

        self.assertIn("10GBASE-T enforces a hard 100m physical boundary", str(cm.exception))

    def test_routing_engine_policy_selection(self):
        sample_subnets = [
            SubnetAllocation("VLAN10", 10, 50, 62, 26, "10.0.0.0", "255.255.255.192", "0.0.0.63", "10.0.0.1", "10.0.0.63", "standard")
        ]

        # Single-site campus
        plan_campus = RoutingEngine.determine_policy(sample_subnets, is_multi_site=False, as_number=65001)
        self.assertIn("Single-Area OSPFv2", plan_campus.protocol)
        self.assertIsNone(plan_campus.border_protocol)

        # Multi-site MAN/WAN
        plan_wan = RoutingEngine.determine_policy(sample_subnets, is_multi_site=True, as_number=65002)
        self.assertIn("Multi-Area OSPFv2", plan_wan.protocol)
        self.assertIn("eBGP Peering", plan_wan.border_protocol)


if __name__ == "__main__":
    unittest.main()
