# NetArchitect

**NetArchitect** is a Python command-line application for deterministic enterprise network planning. It accepts one of three built-in network profiles or a custom JSON specification, then calculates IPv4 subnet allocations, recommends physical transmission media, evaluates topology and routing choices, and generates engineering reports and Cisco IOS configuration baselines.

> **Course:** CIC-307 – Computer Networks  
> **Implementation:** Python 3.10+  
> **Interface:** Command-line application (CLI)  
> **Output:** Markdown design report and Cisco IOS `.cfg` files

---

## Table of contents

- [Project objectives](#project-objectives)
- [Features](#features)
- [How the application works](#how-the-application-works)
- [Technology and requirements](#technology-and-requirements)
- [Repository structure](#repository-structure)
- [Installation](#installation)
- [Running the application](#running-the-application)
- [Built-in network profiles](#built-in-network-profiles)
- [Custom network specification](#custom-network-specification)
- [Generated files](#generated-files)
- [Core algorithms and design decisions](#core-algorithms-and-design-decisions)
- [Running the tests](#running-the-tests)
- [Troubleshooting](#troubleshooting)
- [Scope, assumptions, and limitations](#scope-assumptions-and-limitations)
- [References](#references)

## Project objectives

Enterprise networks have different addressing, scale, distance, availability, and routing requirements. Designing them manually involves several related tasks: allocating subnets without overlap, choosing suitable physical media, selecting an appropriate topology, documenting routing decisions, and preparing device configurations.

NetArchitect brings these tasks into one repeatable workflow. Given a network specification, it:

1. Validates the input and rejects invalid or inconsistent values.
2. Allocates IPv4 subnets using Variable Length Subnet Masking (VLSM).
3. Recommends physical media based on link distance and any requested media constraint.
4. Recommends a topology based on endpoint count, site count, and dual-homing requirements.
5. Recommends a routing policy based on the single-site or multi-site design.
6. Generates a Markdown engineering report and two Cisco IOS configuration baselines.

The application is deterministic: the same valid input produces the same planning decisions and output content.

## Features

### Network profiles and input handling

- Built-in Campus LAN, Metro MAN, and Global WAN JSON profiles.
- Custom network designs supplied through a JSON file.
- Validation of required fields, data types, numeric ranges, IPv4 CIDR notation, VLAN IDs, duplicate subnet names/VLAN IDs, link distances, and bandwidth values.
- Validation that requested subnet allocations fit inside the supplied root IPv4 network.

### IPv4 addressing and VLSM

- Allocates address blocks in descending order of requested host capacity.
- Calculates the required subnet prefix and aligns each allocation to its block boundary.
- Produces network address, subnet mask, wildcard mask, first usable address (used as the default gateway), broadcast address, and usable host count.
- Detects invalid host requests, duplicate VLAN IDs, invalid CIDR input, and address-space exhaustion.

### Physical media recommendations

The media engine uses the configured link distance and optional media override to recommend a medium and associated standard/transceiver information. The current planning assumptions include:

| Link distance / constraint | Recommendation used by the planner |
|---|---|
| Up to 100 m | Cat6a copper, when no fiber-only override is supplied |
| More than 100 m up to 400 m | OM4 multimode fiber |
| More than 400 m up to 10 km | OS2 single-mode fiber with 10GBASE-LR assumption |
| More than 10 km up to 40 km | OS2 single-mode fiber with 10GBASE-ER assumption |
| More than 40 km | Carrier-managed optical transport recommendation (DWDM/OTN) |

The engine rejects a copper override beyond 100 m and an OM4/MMF override beyond 400 m under the planner's 10GBASE-SR assumption. These are planning guardrails, not a substitute for a complete optical link budget or vendor-specific compatibility check.

### Topology and routing recommendations

- Collapsed-core (two-tier) recommendation for a single site with up to 500 endpoints.
- Three-tier hierarchical campus recommendation for a larger single-site network.
- Hierarchical multi-site WAN recommendation when more than one site is specified.
- Dual-homing is reflected in the topology rationale when requested.
- Single-area OSPFv2 is recommended for a single-site design with fewer than 50 allocated subnets.
- Hierarchical multi-area OSPFv2 with an eBGP border recommendation is returned for multi-site designs or designs with 50 or more subnets.

These are design recommendations generated from the supplied metadata. They do not mean that every recommended routing relationship is fully configured or simulated.

### Output generation

Each successful run generates:

1. A Markdown engineering design report.
2. A Layer 2 access-switch configuration baseline.
3. A Layer 3 core/distribution multilayer-switch configuration baseline.

## How the application works

```text
Built-in preset JSON / Custom JSON
              |
              v
       Configuration Loader
              |
              v
        Input Validation
              |
       +------+------+
       |             |
       v             v
   VLSM Engine   Physical Media Engine
       |             |
       +------+------+
              |
              v
    Topology and Routing Engines
              |
              v
       Network Architecture Plan
              |
       +------+----------------+
       |                       |
       v                       v
 Markdown Report       Cisco IOS Generators
       |                       |
       +-----------+-----------+
                   |
                   v
              Output Folder
```

### Main modules

- `core/params.py`: loads JSON files and validates the configuration before planning begins.
- `core/models.py`: typed data structures used to represent subnet requests, allocations, links, recommendations, and the final plan.
- `core/vlsm_engine.py`: calculates IPv4 VLSM allocations using integer arithmetic and Python's IPv4 address/network primitives.
- `core/media_engine.py`: evaluates physical link distances and media constraints.
- `core/topology_engine.py`: recommends a topology from endpoint count, site count, and dual-homing metadata.
- `core/routing_engine.py`: selects a routing-policy recommendation.
- `generators/report_engine.py`: creates the Markdown engineering report.
- `generators/cisco_ios.py`: creates the access-switch and core/distribution IOS configuration baselines.
- `main.py`: command-line parsing, orchestration, and output-file writing.

## Technology and requirements

- Python 3.10 or newer
- `pip` for package installation
- `pytest` for the automated test suite
- Cisco Packet Tracer or compatible Cisco IOS environment for manual configuration review and simulation

The application has no third-party runtime dependencies declared in `pyproject.toml`. Pytest is included as a development/test dependency.

## Repository structure

```text
netarchitect/
├── config/                         # Repository copies of the three JSON presets
│   ├── preset_campus.json
│   ├── preset_metro.json
│   └── preset_wan.json
├── exports/                        # Example generated reports and IOS configurations
├── src/
│   └── netarchitect/
│       ├── core/
│       │   ├── exceptions.py       # Domain-specific exceptions
│       │   ├── media_engine.py     # Physical media recommendation logic
│       │   ├── models.py           # Request and result data models
│       │   ├── params.py           # JSON loading and input validation
│       │   ├── routing_engine.py   # Routing policy recommendation logic
│       │   ├── topology_engine.py  # Topology recommendation logic
│       │   └── vlsm_engine.py      # IPv4 VLSM allocation
│       ├── generators/
│       │   ├── cisco_ios.py        # Cisco IOS configuration generation
│       │   └── report_engine.py    # Markdown report generation
│       ├── presets/                # Presets bundled with the Python package
│       ├── __init__.py
│       └── main.py                 # CLI entry point and orchestration
├── tests/                          # Automated unit and integration tests
├── .gitignore
├── .python-version
├── ai_audit_log.md                 # AI-assisted development record
├── pyproject.toml                  # Package metadata and CLI entry point
├── README.md
└── requirements.txt                # Test dependency list
```

`config/` and `src/netarchitect/presets/` contain copies of the built-in preset files. The application first checks the repository-level `config/` directory and falls back to the packaged presets, allowing the profiles to remain available when the package is installed.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Anshbharadwaj28/netarchitect.git
cd netarchitect
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it using the command for your terminal:

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

**Windows Command Prompt**

```cmd
.venv\Scripts\activate.bat
```

**Linux / macOS / Git Bash**

```bash
source .venv/bin/activate
```

### 3. Install the project

Upgrade pip and install the project in editable mode with its development dependency:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Editable installation makes the `netarchitect` command available in the active virtual environment while using the source code in the working directory.

## Running the application

### Display command-line help

```bash
netarchitect --help
```

The CLI accepts exactly one input source: a built-in preset or a custom JSON file. `--output-dir` is optional and defaults to `exports`.

### Run the Campus LAN profile

```bash
netarchitect --preset campus
```

### Run the Metro MAN profile

```bash
netarchitect --preset metro
```

### Run the Global WAN profile

```bash
netarchitect --preset wan
```

### Choose a different output directory

```bash
netarchitect --preset campus --output-dir exports/campus-run
```

### Run without installing the console command

From the repository root, after dependencies are available:

```bash
python -m netarchitect.main --preset campus
```

### Run a custom design

```bash
netarchitect --input config/my_network.json --output-dir exports/custom
```

A successful run prints a short summary containing the profile, subnet/link counts, topology recommendation, and paths of the generated files. A handled input, planning, or file error is printed to standard error and returns exit code `2`; a successful run returns `0`.

## Built-in network profiles

The repository includes three example inputs. They are illustrative design scenarios and can be edited or used as starting points for custom designs.

| Preset | Scenario | Root IPv4 block | AS number | Multi-site flag |
|---|---|---|---:|---|
| `campus` | Campus LAN with student, faculty, IoT, voice, and CCTV VLANs | `10.100.0.0/16` | 65001 | `false` |
| `metro` | Metro MAN connecting HQ, colocation, and disaster-recovery networks | `172.16.0.0/16` | 65100 | `true` |
| `wan` | Global WAN and multi-cloud connectivity scenario | `10.0.0.0/14` | 64512 | `true` |

Run each profile with the commands in [Running the application](#running-the-application). Generated sample outputs are stored in `exports/` in the repository.

## Custom network specification

A custom input is a UTF-8 JSON object. The following fields are required:

- `root_cidr`: IPv4 network block from which the VLSM allocator assigns subnets.
- `subnets`: non-empty array of subnet requests.
- `links`: non-empty array of physical links to evaluate.

The remaining top-level fields are optional and have defaults described below.

### Example JSON

Save the following as `config/my_network.json`:

```json
{
  "project_name": "Example University Campus",
  "profile_type": "Custom Campus",
  "root_cidr": "10.20.0.0/16",
  "autonomous_system": 65010,
  "is_multi_site": false,
  "endpoints": 250,
  "site_count": 1,
  "dual_homed": true,
  "subnets": [
    {
      "name": "Students",
      "hosts_needed": 180,
      "vlan_id": 10,
      "traffic_class": "bulk"
    },
    {
      "name": "Faculty",
      "hosts_needed": 50,
      "vlan_id": 20,
      "traffic_class": "standard"
    },
    {
      "name": "Voice",
      "hosts_needed": 25,
      "vlan_id": 30,
      "traffic_class": "voice"
    }
  ],
  "links": [
    {
      "source": "Core-Switch",
      "destination": "Access-Switch-01",
      "distance_meters": 85,
      "required_bandwidth_gbps": 10,
      "medium_override": null
    },
    {
      "source": "Core-Switch",
      "destination": "Building-B-Distribution",
      "distance_meters": 250,
      "required_bandwidth_gbps": 10,
      "medium_override": "OM4"
    }
  ]
}
```

Run it with:

```bash
netarchitect --input config/my_network.json --output-dir exports/my-network
```

### Field reference

#### Top-level fields

| Field | Required | Type | Description / validation |
|---|---|---|---|
| `project_name` | No | String | Display name used in generated outputs. Must not be empty when supplied. |
| `profile_type` | No | String | Profile label used in output filenames and reports. Must not be empty when supplied. |
| `root_cidr` | Yes | String | Valid IPv4 CIDR. The allocator supports root prefixes from `/0` through `/30`. |
| `autonomous_system` | No | Integer | AS number from `1` through `4294967295`; defaults to `65000`. |
| `is_multi_site` | No | Boolean | Whether the design spans multiple sites; defaults to `false`. |
| `endpoints` | No | Positive integer | Endpoint count used by the topology engine. Defaults to the sum of requested subnet host counts. |
| `site_count` | No | Positive integer | Number of sites used by the topology engine. Defaults to `2` when `is_multi_site` is true, otherwise `1`. |
| `dual_homed` | No | Boolean | Whether redundant dual-homed uplinks are required; defaults to `false`. |
| `subnets` | Yes | Array | Non-empty list of subnet request objects. |
| `links` | Yes | Array | Non-empty list of physical link objects. |

#### Subnet object

| Field | Required | Type | Description / validation |
|---|---|---|---|
| `name` | Yes | String | Non-empty and unique subnet name. |
| `hosts_needed` | Yes | Integer | Positive requested host count. |
| `vlan_id` | Yes | Integer | Unique VLAN ID from `1` through `4094`. |
| `traffic_class` | No | String | Descriptive traffic category; defaults to `standard`. Example values in the presets are `voice`, `video`, `standard`, and `bulk`. |

#### Link object

| Field | Required | Type | Description / validation |
|---|---|---|---|
| `source` | Yes | String | Non-empty source device/site name. |
| `destination` | Yes | String | Non-empty destination device/site name. |
| `distance_meters` | Yes | Number | Finite, non-negative physical distance in metres. |
| `required_bandwidth_gbps` | No | Number | Positive finite bandwidth in Gbps; defaults to `10.0`. |
| `medium_override` | No | String or `null` | Optional media constraint. Supported values are `CAT6`, `CAT6A`, `COPPER`, `10GBASE-T`, `OM4`, `MMF`, `OS2`, and `SMF` (case-insensitive). |

### Input validation rules

The configuration loader checks that:

- The JSON root is an object and contains `root_cidr`, `subnets`, and `links`.
- The root address is valid IPv4 CIDR and is within the supported prefix range.
- At least one subnet and one link are supplied.
- Every subnet has a non-empty name, positive integer host demand, and valid VLAN ID.
- Subnet names and VLAN IDs are unique.
- The requested VLSM blocks fit inside the root CIDR without overlap.
- Link endpoints are non-empty strings; distances are finite and non-negative.
- Link bandwidth values are positive and finite.
- Optional AS number, endpoint count, site count, booleans, and project labels have valid types and ranges.

Invalid input stops the run with an explanatory error instead of generating a partial design.

## Generated files

For a profile named `Campus LAN`, the application creates these files in the selected output directory (the profile label is converted to lowercase and spaces are replaced with underscores):

```text
exports/
├── campus_lan_design_report.md
├── campus_lan_sw_access.cfg
└── campus_lan_core_router.cfg
```

The exact filenames for other profiles follow the same pattern, for example `metro_man_design_report.md` and `global_wan_core_router.cfg`.

### 1. Markdown design report

The report includes:

- Project and profile metadata.
- Recommended topology and its rationale.
- VLSM allocation table, including VLAN, host demand, usable hosts, prefix, network, subnet mask, wildcard mask, gateway, and broadcast address.
- Physical link distance, recommended medium, transceiver, standard, and engineering rationale.
- Routing protocol recommendation, topology tier, area information, border protocol, and rationale.

### 2. Access-switch configuration (`*_sw_access.cfg`)

The generated Layer 2 baseline includes:

- Hostname `SW-ACCESS-01`.
- VLAN declarations based on the subnet allocations.
- A sample 802.1Q trunk uplink on `GigabitEthernet0/1`.
- Up to three sample access interfaces mapped to the first allocated VLANs.
- Rapid-PVST and default PortFast/BPDU Guard settings.

### 3. Core/distribution configuration (`*_core_router.cfg`)

Despite the historical `core_router` output filename, the generated device configuration is for a **Layer 3 multilayer switch**, with hostname `CORE-SW1`. It includes:

- IP routing and Rapid-PVST.
- VLAN switched virtual interfaces (SVIs) using the calculated gateway addresses.
- OSPF process and network statements for the allocated subnets.
- Example QoS class maps and policy map for voice/video traffic classes.
- A comment describing the eBGP recommendation when the plan is multi-site, without inventing incomplete BGP peer statements.

## Core algorithms and design decisions

### VLSM allocation

The allocator sorts subnet requests by descending host demand so that larger address blocks are assigned first. For each subnet it determines the smallest power-of-two address block that can contain the requested hosts plus the network and broadcast addresses, aligns the next available address to that block boundary, and checks that the block remains within the root network.

For a conventional IPv4 subnet with prefix length `p`, the total address count is:

```text
2^(32 - p)
```

For ordinary subnet sizes, the usable host count is:

```text
2^(32 - p) - 2
```

The implementation uses integer arithmetic for address alignment and Python's `ipaddress` module for IPv4 network representation. The first usable address is selected as the default gateway in generated plans.

### Physical media selection

Media recommendations are based on distance bands and optional override constraints. The engine explicitly guards against copper links beyond 100 m and OM4 links beyond the assumed 400 m 10GBASE-SR reach. For spans beyond 40 km, the planner recommends provider-managed optical transport rather than treating a single 10GBASE-ER optic as sufficient.

### Topology selection

The topology engine uses endpoint count, site count, and the dual-homing flag. The thresholds are deterministic rules encoded in `topology_engine.py`; they are recommendations and do not calculate detailed port counts, oversubscription ratios, failure domains, or physical device quantities.

### Routing selection

The routing engine recommends single-area OSPFv2 for a smaller single-site design and hierarchical OSPFv2 with an eBGP border for multi-site or larger designs. The recommendation is included in the report and informs the generated core baseline. The current configuration generator does not create complete multi-site routing adjacencies.

## Running the tests

Install the development dependency (included by `python -m pip install -e ".[dev]"`) and run:

```bash
python -m pytest -v
```

For a concise summary:

```bash
python -m pytest -q
```

The test suite covers VLSM allocation and validation, media-selection boundaries, routing-policy selection, topology recommendations, invalid configuration handling, preset loading, and CLI output generation.

## Troubleshooting

### `netarchitect` is not recognized

Activate the virtual environment and install the package:

```bash
python -m pip install -e ".[dev]"
```

Alternatively, run the module from the repository root:

```bash
python -m netarchitect.main --preset campus
```

### PowerShell blocks virtual-environment activation

If local policy prevents activation, use the Python executable inside the environment directly:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\netarchitect.exe --preset campus
```

### Address-space exhaustion

Increase the root CIDR capacity or reduce the requested host counts. The allocator will not silently place a subnet outside the specified root network.

### Invalid media override

Use one of the supported values: `CAT6`, `CAT6A`, `COPPER`, `10GBASE-T`, `OM4`, `MMF`, `OS2`, or `SMF`. Also check that the requested distance is within the planner's limit for the selected medium.

### Generated configuration does not match a Packet Tracer device

Interface names and supported IOS commands vary by device model and Packet Tracer version. Select the target device first, then adapt and verify interface identifiers and platform-specific commands. A generated configuration file is a baseline, not a guarantee that every command is supported by every simulated device.

## Scope, assumptions, and limitations

NetArchitect is an educational network-planning and configuration-baseline tool. It is not a network emulator, an automatic Packet Tracer project generator, or a production deployment system.

- **Routing is recommended, not fully deployed.** Multi-area OSPF and eBGP are policy recommendations. The current input schema does not provide WAN router interfaces, peer addresses, remote AS values, authentication settings, or advertised prefixes, so complete site-to-site BGP configurations are not generated.
- **Generated device roles are limited.** The application generates one sample Layer 2 access-switch configuration and one Layer 3 core/distribution multilayer-switch configuration per run. It does not generate a complete per-site device inventory or every router/switch configuration for a real enterprise network.
- **Access ports are illustrative.** Up to three sample access ports are generated, not a complete port plan for every endpoint.
- **QoS is a baseline example.** The class maps and policy map are illustrative and are not automatically attached to a WAN interface. Production QoS requires traffic requirements and platform-specific validation.
- **Security policy is not inferred.** ACLs, firewall rules, VPN policies, and segmentation rules are not invented from generic address ranges. They require explicit security requirements.
- **Media recommendations are simplified.** Actual deployment requires checking optic type, fiber plant, connector, attenuation, splice/patch loss, optical budget, speed, vendor interoperability, and applicable standards for the selected hardware.
- **No Packet Tracer verification is implied.** The generated `.cfg` files must be loaded into the chosen Packet Tracer devices and tested. Simulation screenshots or `.pkt` files should only be included in a submission after that verification has actually been performed.
- **No production readiness is claimed.** Review and adapt every generated command for the exact device model, IOS release, interface naming, and network requirements before use.

## References

The project logic and its engineering assumptions are informed by standard networking concepts and specifications, including:

- RFC 2328 – OSPF Version 2.
- RFC 4271 – A Border Gateway Protocol 4 (BGP-4).
- IEEE 802.3 Ethernet specifications, including 10GBASE-T, 10GBASE-SR, 10GBASE-LR, and 10GBASE-ER physical-layer families.
- ITU-T G.694.1 – Spectral grids for WDM applications: DWDM frequency grid.
- ITU-T G.709 – Interfaces for the Optical Transport Network (OTN).
- Python `ipaddress` documentation for IPv4 address and network handling.

These references provide background for the design concepts. Exact device compatibility and standards compliance must be checked against the hardware and implementation selected for a real deployment.

---

**NetArchitect – CIC-307 Computer Networks Project**  
*Deterministic network planning, IPv4 addressing, media recommendations, routing/topology decisions, and Cisco IOS baseline generation.*
