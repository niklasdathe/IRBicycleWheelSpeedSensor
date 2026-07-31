# Versioning and releases

Hardware and software have independent version streams.

| Stream | Version file | GitHub tag format | Meaning |
|---|---|---|---|
| Hardware | `hardware/VERSION` | `V0.1`, `V0.2`, ... | Ordered or manufactured PCB baseline |
| Software | `firmware/VERSION` | `SW-V0.1.0`, ... | Tested firmware release |

KiCad CAD revision `R4` is an internal design identifier. Hardware `V0.1` is
the ordered release made from that CAD revision. A hardware release never
implies that firmware with a similar number was released.

The `V0.1` annotated Git tag and GitHub release are immutable troubleshooting
anchors. The release contains the combined order package, Gerber archive,
PCBA archive, individual BOM/CPL/order files, DRC evidence, courtyard reference
and SHA-256 checksums.

Development after the ordered baseline uses `V0.2-dev` in
`hardware/VERSION`. Its changelog section records differences relative to
`V0.1`; only an intentionally approved manufacturing state becomes tag `V0.2`.
