import unittest
from netarchitect.core.models import SubnetRequest
from netarchitect.core.vlsm_engine import VLSMEngine
from netarchitect.core.exceptions import SubnetExhaustionError


class TestVLSMEngine(unittest.TestCase):
    def test_vlsm_descending_allocation_and_boundary_alignment(self):
        requests = [
            SubnetRequest(name="Small-Corp", hosts_needed=10, vlan_id=10),
            SubnetRequest(name="Huge-WLAN", hosts_needed=500, vlan_id=20),
            SubnetRequest(name="Mid-Staff", hosts_needed=100, vlan_id=30)
        ]
        allocs = VLSMEngine.calculate_vlsm("192.168.0.0/22", requests)

        self.assertEqual(allocs[0].name, "Huge-WLAN")
        self.assertEqual(allocs[0].prefix_length, 23)
        self.assertEqual(allocs[0].network_address, "192.168.0.0")

        self.assertEqual(allocs[1].name, "Mid-Staff")
        self.assertEqual(allocs[1].prefix_length, 25)
        self.assertEqual(allocs[1].network_address, "192.168.2.0")

        self.assertEqual(allocs[2].name, "Small-Corp")
        self.assertEqual(allocs[2].prefix_length, 28)
        self.assertEqual(allocs[2].network_address, "192.168.2.128")

    def test_vlsm_non_overlapping_bitmasks(self):
        requests = [
            SubnetRequest(name="NetA", hosts_needed=100, vlan_id=10),
            SubnetRequest(name="NetB", hosts_needed=60, vlan_id=20),
            SubnetRequest(name="NetC", hosts_needed=25, vlan_id=30),
            SubnetRequest(name="P2P", hosts_needed=2, vlan_id=40)
        ]
        allocs = VLSMEngine.calculate_vlsm("10.0.0.0/24", requests)

        for i in range(len(allocs) - 1):
            curr_bcast = VLSMEngine._ip_to_int(allocs[i].broadcast_address)
            next_net = VLSMEngine._ip_to_int(allocs[i + 1].network_address)
            self.assertLess(curr_bcast, next_net, f"Overlap detected between {allocs[i].name} and {allocs[i+1].name}")

    def test_vlsm_wildcard_mask_accuracy(self):
        requests = [SubnetRequest(name="PointToPoint", hosts_needed=2, vlan_id=99)]
        allocs = VLSMEngine.calculate_vlsm("10.254.0.0/30", requests)

        self.assertEqual(allocs[0].prefix_length, 30)
        self.assertEqual(allocs[0].subnet_mask, "255.255.255.252")
        self.assertEqual(allocs[0].wildcard_mask, "0.0.0.3")
        self.assertEqual(allocs[0].default_gateway, "10.254.0.1")
        self.assertEqual(allocs[0].broadcast_address, "10.254.0.3")

    def test_vlsm_subnet_exhaustion_raises_exception(self):
        requests = [
            SubnetRequest(name="TooLarge", hosts_needed=30, vlan_id=10)
        ]
        with self.assertRaises(SubnetExhaustionError):
            VLSMEngine.calculate_vlsm("192.168.1.0/28", requests)


if __name__ == "__main__":
    unittest.main()

    def test_invalid_ipv4_cidr_is_rejected(self):
        with self.assertRaises(ValueError):
            VLSMEngine.calculate_vlsm("10.999.0.0/24", [SubnetRequest("A", 10, 10)])

    def test_duplicate_vlan_is_rejected(self):
        with self.assertRaises(ValueError):
            VLSMEngine.calculate_vlsm("10.0.0.0/24", [
                SubnetRequest("A", 10, 10), SubnetRequest("B", 10, 10)
            ])

    def test_noncanonical_root_is_normalized_without_escape(self):
        result = VLSMEngine.calculate_vlsm("10.0.0.17/24", [SubnetRequest("A", 20, 10)])
        self.assertEqual(result[0].network_address, "10.0.0.0")
