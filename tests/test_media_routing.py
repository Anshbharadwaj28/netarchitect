import math
import unittest

from netarchitect.core.models import PhysicalLinkRequest, SubnetAllocation
from netarchitect.core.media_engine import MediaEngine
from netarchitect.core.routing_engine import RoutingEngine
from netarchitect.core.exceptions import PhysicalDistanceViolationError


class TestMediaAndRouting(unittest.TestCase):
    def test_media_selection_boundaries(self):
        # Assignment boundary: <=100m Cat6a; 101-400m OM4; >400m OS2.
        r1 = MediaEngine.evaluate_link(PhysicalLinkRequest("SW1", "SW2", 95.0))
        self.assertIn("Cat6a", r1.recommended_media)
        self.assertIn("802.3an", r1.standard)

        r2 = MediaEngine.evaluate_link(PhysicalLinkRequest("SW1", "SW3", 250.0))
        self.assertIn("OM4", r2.recommended_media)
        self.assertEqual(r2.wavelength_nm, 850)

        r3 = MediaEngine.evaluate_link(PhysicalLinkRequest("SW1", "DC1", 12000.0))
        self.assertIn("OS2", r3.recommended_media)
        self.assertIn("SFP-10G-ER", r3.transceiver_type)

    def test_copper_distance_violation_error(self):
        link = PhysicalLinkRequest("Campus-A", "Campus-B", 140.0, medium_override="Cat6a")
        with self.assertRaises(PhysicalDistanceViolationError) as cm:
            MediaEngine.evaluate_link(link)
        self.assertIn("100m", str(cm.exception))

    def test_routing_engine_policy_selection(self):
        sample = [SubnetAllocation("VLAN10", 10, 50, 62, 26, "10.0.0.0", "255.255.255.192", "0.0.0.63", "10.0.0.1", "10.0.0.63", "standard")]
        campus = RoutingEngine.determine_policy(sample, is_multi_site=False, as_number=65001)
        self.assertIn("Single-Area OSPFv2", campus.protocol)
        self.assertIsNone(campus.border_protocol)
        wan = RoutingEngine.determine_policy(sample, is_multi_site=True, as_number=65002)
        self.assertIn("Multi-Area OSPFv2", wan.protocol)
        self.assertIn("eBGP Peering", wan.border_protocol)

    def test_negative_or_nan_or_infinite_distance_is_rejected(self):
        for distance in (-1, math.nan, math.inf, -math.inf):
            with self.subTest(distance=distance):
                with self.assertRaises(ValueError):
                    MediaEngine.evaluate_link(PhysicalLinkRequest("A", "B", distance))


def test_distance_beyond_40km_uses_carrier_managed_transport():
    link = PhysicalLinkRequest("A", "B", 40001)

    result = MediaEngine.evaluate_link(link)

    assert "OS2" in result.recommended_media
    assert "Carrier-managed" in result.recommended_media
    assert "DWDM/OTN" in result.recommended_media
    assert "exceeds ordinary 10GBASE-LR/ER" in result.engineering_justification




if __name__ == "__main__":
    unittest.main()
