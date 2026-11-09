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