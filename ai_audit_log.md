# AI Code Audit and Technical Defense Log

**Course:** CIC-307 Computer Networks Mini-Project  
**Project:** NetArchitect  
**Purpose:** Record concrete defects found during AI-assisted development, explain their technical impact, and document remediation.  
**Status:** Source-level and automated-test verification performed; Packet Tracer/GNS3 simulation must be recorded separately after it is actually completed.

---

## Incident 1: Incorrect VLSM block sizing and wildcard-mask reasoning

### Prompt / task context

The development task was to generate a VLSM allocator that accepts a parent IPv4 prefix and a list of host requirements, then allocates non-overlapping subnets in descending host-count order.

### Flawed AI-proposed approach

An unsafe simplified approach considered during development was:

```python
import ipaddress

def allocate_subnet(current_ip, host_count):
    # Incorrect: host_count.bit_length() alone does not correctly
    # reserve network and broadcast addresses or prove alignment.
    prefix = 32 - host_count.bit_length()
    return ipaddress.IPv4Network(f"{current_ip}/{prefix}", strict=False)


def wildcard_from_mask(mask):
    # This arithmetic is only safe after validating four octets
    # and a contiguous IPv4 netmask.
    octets = [int(part) for part in mask.split(".")]
    return ".".join(str(255 - octet) for octet in octets)
```

### Technical diagnosis

1. Traditional IPv4 subnets reserve a network address and a broadcast address. The requested usable host count therefore cannot be treated as the total number of addresses.
2. The required block must be a power of two large enough for `hosts_needed + 2` addresses (for ordinary subnets), with a minimum block size of four addresses for a `/30`.
3. Every subnet start must be aligned to its block size. Merely constructing a network with `strict=False` can silently normalize an address and conceal allocator mistakes.
4. A wildcard mask is the bitwise inverse of a valid contiguous subnet mask. Octet subtraction is not a substitute for validating that the input is a legal netmask.

### Remediation in the project

The VLSM engine uses Python's `ipaddress` module for IPv4 parsing and integer arithmetic for block alignment. It sorts requests by descending host count, computes a power-of-two block, checks the parent-network boundary, and derives the wildcard mask from the network netmask.

Relevant implementation: `src/netarchitect/core/vlsm_engine.py`.

### Verification

The test suite includes descending allocation, non-overlap, `/30` wildcard-mask accuracy, invalid CIDR rejection, duplicate VLAN rejection, noncanonical parent-prefix normalization, and address-space exhaustion.

### Packet-flow impact

An incorrect subnet boundary can place a host in a different prefix than the routing table or ACL expects. A packet may then be routed toward the wrong next hop, fail to reach its destination, or bypass a policy written for the intended destination prefix. The allocator must therefore prove alignment and non-overlap before configuration generation.

---

## Incident 2: Escaped newline characters in generated Cisco ACL files

### Prompt / task context

The task was to generate a copy-paste-ready Cisco IOS extended ACL configuration as a Python string and write it to a `.cfg` file.

### Flawed AI-generated code

```python
def render_acl(lines):
    # BUG: double escaping produces literal backslash-n characters.
    return "\\n".join(lines) + "\\n"
```

### Technical diagnosis

In a Python string literal, `"\\n"` represents the two visible characters backslash and `n`; it is not a line terminator. The resulting file becomes one long line containing literal `\n` sequences. A human can read the intended commands, but the file is not a correctly line-delimited IOS configuration and cannot be reliably pasted or processed as separate commands.

### Corrected code

```python
def render_acl(lines):
    # A single escaped newline creates an actual line break.
    return "\n".join(lines) + "\n"
```

### Remediation in the project

The ACL generator returns `"\n".join(lines) + "\n"`, using actual newline characters. The generator continues to derive the destination network and wildcard mask from the VLSM allocation associated with the destination VLAN.

Relevant implementation: `src/netarchitect/core/acl_engine.py`.

### Verification

The generated `custom_test_security_acl.cfg` was inspected and its commands appeared on separate lines. Automated ACL tests verify policy rendering and validation. Regenerate the file after any further source changes and inspect it before submission.

### Packet-flow impact

The intended policy is to filter packets entering the source VLAN's SVI. If the configuration file is malformed and the ACL is not correctly entered on the device, the intended deny rule is not installed. Traffic from the source VLAN to the protected destination VLAN may therefore be routed without the intended filter. After applying the ACL, verify the attachment with `show ip interface vlan <id>` and rule counters with `show access-lists`.

---

## Verification record

The project was checked using the following commands in the development environment:

```powershell
python -m pip install -e .
python -m pytest -v
python -m netarchitect.main --preset campus --output-dir exports/campus
python -m netarchitect.main --preset metro --output-dir exports/metro
python -m netarchitect.main --preset wan --output-dir exports/global
python -m netarchitect.main --input config/custom_test.json --output-dir exports/custom_test
```

**Important:** The test count and command outcomes must be updated to match the final run on the student's machine. Packet Tracer/GNS3 simulation is not claimed here. Add dated screenshots and observed ping/ACL/routing results only after performing those tests.

## Limitations disclosed

- Generated configurations are baselines and require device-model and interface-specific review.
- A recommendation for eBGP or multi-area OSPF is not proof of a complete adjacency configuration. Real peer addresses, AS numbers, interface mappings, and area assignments are required.
- Packet Tracer/GNS3 validation remains a separate deliverable until the configurations have actually been loaded and tested.
- ACL policies are configurable. The example `permit ip any any` after a specific deny is permissive for all other IPv4 traffic and must be reviewed against the intended security policy.
