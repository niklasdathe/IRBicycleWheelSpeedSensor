# Interactive BOM

[Open the generated Interactive HTML BOM](interactive_bom.html).

The page is generated directly from
`hardware/ir_spoke_link/ir_spoke_link.kicad_pcb`. It contains the front board
drawing, fabrication/silkscreen/pads, tracks, nets, placement checkboxes and a
searchable grouped BOM with manufacturer, MPN, LCSC and JLC classification.
Clicking a BOM row highlights the footprint; entering a reference such as
`D1` in **Ref lookup** selects it on the board.

## Live KiCad synchronization

Run:

```powershell
.\Open-Interactive-BOM.cmd
```

The watcher serves `http://127.0.0.1:8766/interactive_bom.html`, monitors the
authoritative PCB and regenerates after every complete save. The served page
reloads automatically when its output hash changes. Opening the normal KiCad
launcher starts the same watcher before Pcbnew.

The committed HTML remains fully self-contained and works offline without the
watcher. Browser checkbox state is local to the browser and is not part of the
KiCad design.

## Reproduce or verify

The setup script installs the pinned upstream release outside the repository:

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup_interactive_bom.ps1
py -3.14 tools\interactive_bom.py --generate
py -3.14 tools\interactive_bom.py --check
```

The tool is pinned to
[openscopeproject/InteractiveHtmlBom v2.11.2](https://github.com/openscopeproject/InteractiveHtmlBom/releases/tag/v2.11.2),
commit `de7fad7ead9b73cea7eb17afa02c6ce9ce17a6ab`. The generator runs with KiCad
10's bundled Python/`pcbnew`, so board parsing uses the same KiCad major
version as the project.

`interactive_bom.json` records the PCB SHA-256, HTML SHA-256, generator
version and complete option list. Repository checks fail if either file is
stale or modified independently.

## Publication

GitHub Pages publishes the `docs/` directory. After Pages is enabled for the
repository, the stable URL is:

`https://niklasdathe.github.io/IRBicycleWheelSpeedSensor/interactive_bom.html`
