# AI Code Audit & Academic Defense Log

**Course Code:** CIC-307 Computer Networks Mini-Project  
**Tool Name:** NetArchitect  
**System Role:** Lead Network Architect & Systems Auditor  

---

## Incident 1: Flawed Subnet Wildcard Bitwise Math Under Variable Bitshifts

### 1. Initial Generative AI Output (Buggy Python)
```python
def calculate_wildcard(subnet_mask_str):
    # AI proposed string-splitting without validating 32-bit uint boundaries
    octets = [int(x) for x in subnet_mask_str.split(".")]
    wildcard = [str(255 - x) for x in octets]
    return ".".join(wildcard)


def allocate_subnet(current_ip, host_count):
    # Hallucinated naive addition without power-of-two prefix rounding
    import ipaddress
    net = ipaddress.IPv4Network(f"{current_ip}/{32 - (host_count.bit_length())}", strict=False)
    return net
## Repository review and engineering improvements (November 2026)

A source-level review compared this repository with the companion CIC-307 NetArchitect implementation. The following changes were made while retaining this repository's `src/netarchitect` architecture:

- Added centralized JSON configuration validation for required fields, host counts, VLAN ranges/uniqueness, CIDR validity, link distances/bandwidth, AS number, and topology metadata.
- Added a topology decision engine for collapsed-core, three-tier campus, and multi-site WAN recommendations, including dual-homing rationale.
- Reworked VLSM CIDR parsing around Python's `ipaddress` module and integer block alignment; added direct API validation for host requests, names, and VLAN IDs.
- Added finite/non-negative media-distance checks, supported override validation, copper/OM4 reach guardrails, and a carrier-managed DWDM/OTN recommendation for long-haul spans beyond ordinary 10GBASE-ER reach.
- Replaced the placeholder package entry point with the actual CLI and corrected package metadata to support Python 3.10+ and an installable `netarchitect` command.
- Made preset resolution independent of the current working directory and packaged preset JSON files for installed distributions.
- Removed an IOS trunk-encapsulation command that is unsupported on some Catalyst 2960 models, removed a root-guard command from the uplink role, and removed a hard-coded ACL that did not correspond to user-supplied security policy.
- Removed the fabricated BGP peer address/AS from generated configuration. The report and config now explicitly state that real WAN peer metadata is required before BGP neighbor configuration can be emitted.
- Expanded tests to cover all three presets, custom-input validation, topology decisions, invalid CIDRs, duplicate VLANs, non-finite distances, long-haul optics, and CLI output generation.

Validation performed in the working environment: editable package installation succeeded; all three presets generated reports and IOS baseline files; `python -m pytest -q` passed **17 tests**. Packet Tracer simulation was not run during this code review, so generated configurations still require device-specific verification before being represented as simulated evidence.
