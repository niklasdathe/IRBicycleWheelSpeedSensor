# JLC diode orientation verification

JLC CPL rotation is positive counter-clockwise. JLC defines package zero from
the tape/reel orientation and requires the assembly preview and polarity marks
to be checked.

| Ref | Part | Physical KiCad zero | LCSC-owned EasyEDA package zero | CPL offset | Final CPL |
|---|---|---|---|---:|---:|
| D1 | VSMB1940X01 / C3151600 | pad 1 cathode left; pad 2 anode right | pin/pad 1 anode left; pin/pad 2 cathode right | 180° | 180° |
| D2 | VEMD10940FX01 / C7104273 | pad 1 cathode left; pad 2 mechanical center; pad 3 anode right | pin/pad 1 cathode left; pin/pad 2 mechanical center; pin/pad 3 anode right | 0° | 0° |

Electrical maps:

- D1.1 = `LED_K_REMOTE`, D1.2 = `LED_A`.
- D2.1 = `+3V3`, D2.2 = `NC_MECHANICAL`, D2.3 = `PD_ANODE`.

The LCSC package records were read from:

- `https://easyeda.com/api/products/C3151600/components?version=6.5.37`
- `https://easyeda.com/api/products/C7104273/components?version=6.5.37`

Both records identify `owner.username = lcsc`. C3151600's EasyEDA symbol maps
pin 1 to A and pin 2 to K, while KiCad's LED convention maps pad 1 to K and pad
2 to A. D1 therefore needs a CPL-only 180° correction. C7104273 maps pin 1 to
the cathode and pin 3 to the anode, so D2 needs no correction.

The generator binds each rotation rule to reference, LCSC number and MPN and
aborts if those fields no longer match. `hardware/footprint_audit.py`
independently verifies physical rotation and diode pad/net polarity. In the JLC
assembly preview, both parts must read cathode on the left and anode on the
right (`- D1 +` and `- D2 +`).
