# Documentation

Start with the row that matches the job in front of you.

## Task guides

| Task | Use this | Result |
|---|---|---|
| Learn what the sensor does | [System overview](system_overview.md) | Signal chain, modulation and boundaries |
| Set up and run the project | [Getting started](getting_started.md) | KiCad, simulator and complete checks |
| Change code, parameters or CAD | [Development workflow](development.md) | Correct source, generator and acceptance gate |
| Fabricate or assemble R4 | [Manufacturing](manufacturing.md) | JLC package and review checklist |
| Locate and place components | [Interactive BOM workflow](interactive_bom.md) | Live KiCad-synced HTML BOM |
| Test a physical prototype | [Bring-up and test](bringup.md) | Testpoint sequence and pass evidence |

## Engineering references

| Subject | Reference |
|---|---|
| RMT versus MCPWM decision | [ADR-001](architecture_decision.md) |
| RMT field-to-datasheet traceability | [RMT traceability](rmt_traceability.md) |
| Model and generator relationships | [Executable relationships](model_relationships.md) |
| KiCad/SPICE net contract | [Connectivity contract](connectivity_contract.md) |
| Threshold, testpoints and daylight filter | [Debug and threshold policy](debug_and_threshold.md) |
| Power model | [Power budget](power_budget.md) |
| Optional XIAO CAN interface | [CAN interface](can_interface.md) |
| JLC/Konnect setup | [Konnect and JLCPCB](konnect_jlcpcb.md) |
| Diode assembly polarity | [JLC diode orientation](jlc_diode_orientation.md) |
| Documentation design references | [Reference projects](reference_projects.md) |

## Evidence and machine-readable data

| Artifact | Purpose |
|---|---|
| [`requirements/requirements.yaml`](../requirements/requirements.yaml) | Verifiable requirement statements |
| [Verification matrix](../requirements/verification_matrix.md) | Requirement test and evidence mapping |
| [`datasheet_values.json`](datasheet_values.json) | Extracted limits used by checks |
| [Sources](sources.md) | Primary-source index |
| [`zotero_links.json`](zotero_links.json) | Zotero keys and local attachments |
| [Interactive HTML BOM](interactive_bom.html) | Searchable board/part placement view |
| [Technical simulator reference](../local_simulator/technical.html) | Compact live-model trace definitions |
| [R4 panel image](images/ir_spoke_sensor_panel_r4_top.png) | Current captured PCB |
| [Schematic PDF](../hardware/ir_spoke_link/ir_spoke_link_schematic.pdf) | Current generated schematic |
| [Board STEP](../hardware/ir_spoke_link/ir_spoke_link.step) | Mechanical exchange model |

## Information ownership

Each fact has one owner:

- `config/system.json` owns tunable values.
- `hardware/connectivity.json` owns electrical topology.
- `hardware/component_catalog.json` owns part and procurement metadata.
- `hardware/ir_spoke_link/layout_manifest.json` owns captured layout hashes.
- `requirements/requirements.yaml` owns acceptance requirements.
- `project_manifest.json` owns canonical paths and revision.

Other pages explain or link these values; they must not become independent
configuration sources. `tools/audit_project.py` checks canonical paths,
relative documentation links and index coverage.
