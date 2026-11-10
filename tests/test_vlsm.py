import unittest

from netarchitect.core.models import SubnetRequest
from netarchitect.core.vlsm_engine import VLSMEngine
from netarchitect.core.exceptions import SubnetExhaustionError


class TestVLSMEngine(unittest.TestCase):
    def test_vlsm_descending_allocation_and_boundary_alignment(self):
        requests = [
            SubnetRequest(name="Small-Corp", hosts_needed=10, vlan_id=10),
            SubnetRequest(name="Huge-WLAN", hosts_needed=500, vlan_id=20),
            SubnetRequest(name="Mid-Staff", hosts_needed=100, vlan_id=30),
        ]
        allocs = VLSMEngine.calculate_vlsm("192.168.0.0/22", requests)
        self.assertEqual((allocs[0].name, allocs[0].prefix_length, allocs[0].network_address), ("Huge-WLAN", 23, "192.168.0.0"))
        self.assertEqual((allocs[1].name, allocs[1].prefix_length, allocs[1].network_address), ("Mid-Staff", 25, "192.168.2.0"))
        self.assertEqual((allocs[2].name, allocs[2].prefix_length, allocs[2].network_address), ("Small-Corp", 28, "192.168.2.128"))

    def test_vlsm_non_overlapping_bitmasks(self):
        requests = [SubnetRequest("NetA", 100, 10), SubnetRequest("NetB", 60, 20), SubnetRequest("NetC", 25, 30), SubnetRequest("P2P", 2, 40)]
        allocs = VLSMEngine.calculate_vlsm("10.0.0.0/24", requests)
        for current, following in zip(allocs, allocs[1:]):
            self.assertLess(VLSMEngine._ip_to_int(current.broadcast_address), VLSMEngine._ip_to_int(following.network_address))

    def test_vlsm_wildcard_mask_accuracy(self):
        alloc = VLSMEngine.calculate_vlsm("10.254.0.0/30", [SubnetRequest("PointToPoint", 2, 99)])[0]
        self.assertEqual(alloc.prefix_length, 30)
        self.assertEqual(alloc.subnet_mask, "255.255.255.252")
        self.assertEqual(alloc.wildcard_mask, "0.0.0.3")
        self.assertEqual(alloc.default_gateway, "10.254.0.1")
        self.assertEqual(alloc.broadcast_address, "10.254.0.3")

    def test_vlsm_subnet_exhaustion_raises_exception(self):
        with self.assertRaises(SubnetExhaustionError):
            VLSMEngine.calculate_vlsm("192.168.1.0/28", [SubnetRequest("TooLarge", 30, 10)])

    def test_invalid_ipv4_cidr_is_rejected(self):
        with self.assertRaises(ValueError):
            VLSMEngine.calculate_vlsm("10.999.0.0/24", [SubnetRequest("A", 10, 10)])

    def test_duplicate_vlan_is_rejected(self):
        with self.assertRaises(ValueError):
            VLSMEngine.calculate_vlsm("10.0.0.0/24", [SubnetRequest("A", 10, 10), SubnetRequest("B", 10, 10)])

    def test_noncanonical_root_is_normalized_without_escape(self):
        result = VLSMEngine.calculate_vlsm("10.0.0.17/24", [SubnetRequest("A", 20, 10)])
        self.assertEqual(result[0].network_address, "10.0.0.0")


if __name__ == "__main__":
    unittest.main()
