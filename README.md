# NetArchitect: Autonomous Enterprise Network Engine

**Course Code:** CIC-307 --- Computer Networks\
**System Role:** Principal Network Architect & Senior Systems Engineer\
**Language & Frameworks:** Python 3.10+, Pytest, Jinja2\
**Architecture:** Standard Python `src/` Layout

------------------------------------------------------------------------

## 1. Executive Summary

**NetArchitect** is a production-grade software engine designed to
automate enterprise network design, Layer 1--3 physical and logical
resource allocation, and Cisco IOS configuration generation.

By ingesting network parameter specifications via standard JSON
declarations, NetArchitect applies deterministic algorithmic decision
engines to:

-   Enforce physical media physics constraints (IEEE 802.3an / IEEE
    802.3ae).
-   Compute bitwise non-overlapping Variable Length Subnet Masks (VLSM).
-   Select optimal Layer 3 routing topologies and policies (OSPFv2 /
    eBGP).
-   Synthesize deployment-ready Cisco IOS device configurations and
    architectural explainability reports.

------------------------------------------------------------------------

## 2. Directory & Repository Structure

NetArchitect adopts a standard Python `src/` layout to isolate
installable application packages from test suites and top-level
execution tools:

``` text
netarchitect/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated Pytest CI workflow on push/PR
├── config/                      # Ingestion preset profiles
│   ├── preset_campus.json       # Profile 1: Campus LAN (3 bldgs, <400m, 1600 hosts)
│   ├── preset_metro.json        # Profile 2: Metro MAN (HQ + 2 remote 15-35km, FinTech Colo)
│   └── preset_wan.json          # Profile 3: Global WAN (4 cities + cloud VPC)
├── exports/                     # Target directory for generated outputs (.cfg and .md)
│   └── .gitkeep                 # Git tracking anchor for directory structure
├── src/
│   └── netarchitect/
│       ├── __init__.py          # Package initialization (__version__ = "1.0.0")
│       ├── cli.py               # CLI entry point (argparse parser driver)
│       ├── core/                # Core decision engines & dataclass schemas
│       │   ├── __init__.py
│       │   ├── exceptions.py    # Custom domain exceptions
│       │   ├── media_engine.py  # Layer 1/2 Physical Media Physics Engine
│       │   ├── models.py        # Strongly typed Pydantic/Dataclass domain models
│       │   ├── routing_engine.py# Layer 3 Dynamic Routing Policy Engine
│       │   └── vlsm_engine.py   # Bitwise Descending VLSM Allocator Engine
│       └── generators/          # Configuration & Markdown rendering modules
│           ├── __init__.py
│           ├── cisco_ios.py     # Cisco IOS L2 switch & L3 router configuration engine
│           └── report_engine.py # Markdown architectural explainability log generator
├── tests/                       # Automated Pytest unit test suite
│   ├── __init__.py
│   ├── test_media_routing.py    # Physical distance boundaries & copper violation tests
│   └── test_vlsm.py             # Bitwise non-overlap, /30 masks, exhaustion checks
├── .gitignore                   # Version control exclusion rules
├── ai_audit_log.md              # Academic post-mortem of AI bugs caught and fixed
├── pyproject.toml               # Modern Python package build specification
├── README.md                    # Technical reference, setup & workflow guide
└── requirements.txt             # Dependency declarations (pytest, jinja2)
```

------------------------------------------------------------------------

## 3. Algorithmic Decision Engine Specifications

### 3.1. Physical Media Engine (Layer 1 / Layer 2 Physics)

  -----------------------------------------------------------------------
  Link distance           Recommended medium      Technical basis
  ----------------------- ----------------------- -----------------------
  `≤ 100 m`               Cat6a U/FTP             IEEE 802.3an 10GBASE-T,
                                                  500 MHz electrical
                                                  bandwidth

  `101 m – 400 m`         OM4 Multi-Mode Fiber    IEEE 802.3ae
                                                  10GBASE-SR, 850 nm
                                                  VCSEL, 4700 MHz·km
                                                  modal bandwidth

  `> 400 m`               OS2 Single-Mode Fiber   IEEE 802.3ae
                                                  10GBASE-LR/ER,
                                                  1310/1550 nm laser,
                                                  optical attenuation ≤
                                                  0.4 dB/km
  -----------------------------------------------------------------------

**Violation guardrail:** If a user forces copper media for a link
exceeding `100 m`, the engine immediately raises a
`PhysicalDistanceViolationError`.

### 3.2. VLSM Subnetting Engine (Bitwise Integer Math)

-   **Input:** Base Root CIDR (e.g. `10.0.0.0/16`) and required host
    counts per VLAN.
-   **Sorting:** Enforces strict descending ordering by host demand
    prior to memory alignment to prevent address-space fragmentation.
-   **Power-of-two math:** Calculates host bit allocations dynamically:

\[ `\text{host\_bits}`{=tex} =
`\max`{=tex}`\left`{=tex}(2,`\left`{=tex}`\lceil`{=tex}`\log`{=tex}\_2(`\text{hosts\_needed}`{=tex}+2)`\right`{=tex}`\rceil`{=tex}`\right`{=tex})
\]

**Calculated parameters:**

-   Network ID
-   Subnet Mask
-   Cisco Inverted Wildcard Mask
-   Default Gateway (`+1`)
-   Directed Broadcast Address

**Exhaustion guardrail:** Raises a `SubnetExhaustionError` if total
requested address blocks exceed the capacity of the root CIDR block.

### 3.3. Layer 3 Dynamic Routing Policy Engine

-   **Single campus / fewer than 50 subnets:** Provisions Single-Area
    OSPFv2 (Area 0) for flat microsecond Dijkstra SPF convergence
    without ABR overhead (RFC 2328).
-   **Multi-site / cloud border:** Provisions Hierarchical Multi-Area
    OSPFv2 with ABR route summarization, coupled with eBGP peering for
    external WAN/cloud interconnect boundaries (RFC 4271).

------------------------------------------------------------------------

## 4. Complete Setup & Installation Guide

### Prerequisites

-   Python 3.10, 3.11, 3.12, or 3.13
-   Git version control system

### Step 1: Clone the repository

``` bash
git clone https://github.com/your-username/netarchitect.git
cd netarchitect
```

Replace `your-username` with the actual GitHub account or organization
that owns the repository.

### Step 2: Configure a virtual environment

**Linux / macOS:**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (Git Bash):**

``` bash
python -m venv .venv
source .venv/Scripts/activate
```

**Windows (PowerShell):**

``` powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies and the editable package

``` bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

------------------------------------------------------------------------

## 5. End-to-End System Workflow & Execution Guide

Execute the engine using Python's module invocation syntax:

``` bash
python -m netarchitect.cli
```

### Execution workflow

``` text
[ Preset JSON / Custom JSON Input ]
                 |
                 v
       +------------------+
       |    CLI Driver    |
       +--------+---------+
                |
                +----> 1. Ingest link and subnet requests
                |
                +----> 2. Execute VLSMEngine (bitwise VLSM calculation)
                |
                +----> 3. Execute MediaEngine (L1/L2 media physics evaluation)
                |
                +----> 4. Execute RoutingEngine (L3 routing policy evaluation)
                |
                v
       +------------------+
       | Generators Module|
       +--------+---------+
                |
                +----> CiscoIOSGenerator (.cfg syntax rendering)
                |
                +----> ReportEngine (.md architectural log rendering)
                |
                v
       [ Outputs saved to exports/ ]
```

### Running built-in presets

#### Preset 1: Campus LAN Profile

Ingests 3 campus buildings (links under 400 m, 1600 total hosts across 5
VLANs):

``` bash
python -m netarchitect.cli --preset campus --output-dir exports
```

#### Preset 2: Metro MAN Profile

Ingests HQ to 2 remote data centers (15--35 km OS2 links, FinTech
colocation):

``` bash
python -m netarchitect.cli --preset metro --output-dir exports
```

#### Preset 3: Global WAN & Multi-Cloud Profile

Ingests 4 international edge nodes, 2000 IoT devices, and hybrid cloud
VPC interconnects:

``` bash
python -m netarchitect.cli --preset wan --output-dir exports
```

### Running custom input configurations

To run custom parameter specifications, pass the path to your custom
JSON file:

``` bash
python -m netarchitect.cli --input config/preset_campus.json --output-dir exports
```

------------------------------------------------------------------------

## 6. Generated Export Artifacts

Upon running `netarchitect.cli`, three primary production artifacts are
written directly into the `exports/` folder:

  -----------------------------------------------------------------------
  Artifact                            Description
  ----------------------------------- -----------------------------------
  `<profile>_design_report.md`        Complete Markdown design
                                      documentation detailing bitwise
                                      VLSM tables, Layer 1 transceiver
                                      selections, optical physics
                                      rationales, and routing policy
                                      justifications.

  `<profile>_sw_access.cfg`           Copy-paste Cisco IOS configuration
                                      for Layer 2 access switches (VLAN
                                      database, 802.1Q trunking,
                                      Rapid-PVST, Root Guard, BPDU
                                      Guard).

  `<profile>_core_router.cfg`         Copy-paste Cisco IOS configuration
                                      for Layer 3 core routers (SVIs,
                                      `ip routing`, dynamic OSPF network
                                      statements with inverse wildcard
                                      masks, eBGP neighbor peering,
                                      DiffServ QoS
                                      class-maps/policy-maps).
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 7. Comprehensive Testing Guide & Verification

NetArchitect includes a Pytest test suite covering bitwise math,
non-overlapping subnet allocations, distance boundaries, exception
handling, and routing protocol selection.

### Running Pytest

``` bash
python -m pytest -v
```

### Test suite breakdown

  ---------------------------------------------------------------------------------------------------------------------
  Test case name                                             Target module           What it tests / verifies
  ---------------------------------------------------------- ----------------------- ----------------------------------
  `test_vlsm_descending_allocation_and_boundary_alignment`   `vlsm_engine.py`        Verifies host-based descending
                                                                                     sort and power-of-two address
                                                                                     block alignment.

  `test_vlsm_non_overlapping_bitmasks`                       `vlsm_engine.py`        Verifies zero address overlap
                                                                                     between adjacent network blocks.

  `test_vlsm_wildcard_mask_accuracy`                         `vlsm_engine.py`        Validates `/30` point-to-point
                                                                                     subnets, inverted Cisco wildcard
                                                                                     masks, default gateways, and
                                                                                     broadcast addresses.

  `test_vlsm_subnet_exhaustion_raises_exception`             `vlsm_engine.py`        Confirms `SubnetExhaustionError`
                                                                                     is raised when allocations
                                                                                     overflow base CIDR boundaries.

  `test_media_selection_boundaries`                          `media_engine.py`       Validates media selections across
                                                                                     Cat6a (≤ 100 m), OM4 (101--400 m),
                                                                                     and OS2 (\> 400 m) spans.

  `test_copper_distance_violation_error`                     `media_engine.py`       Confirms
                                                                                     `PhysicalDistanceViolationError`
                                                                                     is raised when copper is forced
                                                                                     beyond 100 m.

  `test_routing_engine_policy_selection`                     `routing_engine.py`     Validates OSPF Single-Area
                                                                                     vs. Multi-Area OSPF + eBGP policy
                                                                                     selection rules.
  ---------------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 8. Critical System Principles & Important Points

### Strict bitwise math engine

VLSM calculation strictly avoids external abstraction libraries such as
Python's `ipaddress`, performing pure 32-bit integer bit shifts (`<<`,
`>>`), bitwise XOR (`^`), and bitwise AND (`&`) to guarantee zero
overlap and correct wildcard-mask inversion.

### 100 m electrical channel limit enforcement

Hard physical guardrails prevent invalid network deployments
(e.g. forcing Cat6a over 100 m) by throwing explicit domain exceptions.

### Hardened Cisco security defaults

Generated switch and router configurations explicitly include security
features such as:

-   `spanning-tree portfast bpduguard default`
-   `spanning-tree guard root`
-   `switchport nonegotiate`

### Academic post-mortem transparency

The included `ai_audit_log.md` documents two realistic AI networking
failure modes (wildcard-mask bitshift errors and missing trunk/root
guard protections) and their mathematical or architectural fixes.
