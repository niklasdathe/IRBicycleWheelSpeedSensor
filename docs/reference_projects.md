# Documentation reference projects

Reviewed 2026-07-31. These are reference patterns, not a universal ranking.
They were selected because each makes a mature hardware project easy to enter
without requiring a large front page.

## Framework Laptop 13

Repository:
[FrameworkComputer/Framework-Laptop-13](https://github.com/FrameworkComputer/Framework-Laptop-13)

Useful pattern: a one-sentence scope followed by direct, module-oriented links
to CAD, drawings, connector pinouts and electrical documentation. Licensing is
visible near the top.

Applied here: the root README now routes directly to system, development,
manufacturing, testing and authoritative artifacts instead of narrating the
repository history.

## Libre Solar BMS C1

Repository:
[LibreSolar/bms-c1](https://github.com/LibreSolar/bms-c1)

Useful pattern: prototype maturity is visible immediately, followed by direct
links to schematic, BOM, interactive BOM, firmware, manual, mechanical files
and a test report. Hardware and documentation licenses are explicit.

Applied here: R4 status separates automated evidence from pending physical
validation, and manufacturing/test artifacts are reachable from the first
page.

## HackRF

Repository:
[greatscottgadgets/hackrf](https://github.com/greatscottgadgets/hackrf)

Useful pattern: hardware, firmware, host software and documentation have clear
top-level ownership. The README directs users to built documentation,
troubleshooting and the exact local documentation build command.

Applied here: task guides own procedures, technical references own rationale,
and the getting-started guide states commands plus expected outcomes.

## LumenPnP

Repository:
[opulo-inc/lumenpnp](https://github.com/opulo-inc/lumenpnp)

Useful pattern: stable releases are distinguished from development branches;
exported fabrication artifacts are attached to releases; the roadmap defines
completion in terms of BOM, build guide, usage guide and lifetime tests.

Applied here: R4 is called a release candidate rather than a validated product,
the JLC output is versioned, and physical validation remains a visible release
gate.

## Adopted documentation rules

1. State purpose and maturity before detail.
2. Navigate by user task, not only by file type.
3. Link directly to usable hardware artifacts.
4. Separate generated evidence, inspection and physical measurement.
5. Give every value and relationship one authoritative owner.
6. Put exact commands beside their expected result.
7. Keep release artifacts versioned and development state clearly marked.
8. Make licensing status explicit.
