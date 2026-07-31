# Sources and assumptions

## Geometry

- 700C / 29-inch class effective rolling diameter assumed: 0.702 m.
- Maximum design speed: 60 km/h; stress case: 80 km/h.
- 32 round spokes, 2.0 mm projected width.
- Optical crossing radius: 0.25 m from hub.

At 60 km/h this gives 7.56 wheel revolutions/s, 241.9 spoke passages/s,
approximately 168 µs blocked per spoke and 3.97 ms clear between spokes.

## Primary references

- JLCPCB PCB capabilities:
  https://jlcpcb.com/capabilities/pcb-capabilities/
- JLCPCB PCB assembly FAQ and Basic/Extended classification:
  https://jlcpcb.com/help/article/pcb-assembly-faqs
- JLCPCB assembly DFM terms:
  https://jlcpcb.com/help/article/terms-and-conditions-of-jlcpcb-assembly-service
- Vishay VSMB1940X01 940 nm IR LED, LCSC C3151600:
  https://www.lcsc.com/product-detail/C3151600.html
- Vishay VEMD10940FX01 side-view photodiode, LCSC C7104273:
  https://www.vishay.com/docs/84217/vemd10940fx01.pdf
- Vishay packaging and tape orientation (VSMB1940X01 Fig. 32):
  https://www.vishay.com/docs/80090/packaging.pdf
- JLCPCB placement rotation and zero-orientation rules:
  https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly
  https://jlcpcb.com/help/article/pcb-assembly-faqs-part-2
- TI TLV9062 10 MHz RRIO dual op amp, LCSC C2867884:
  https://www.ti.com/lit/ds/symlink/tlv9062.pdf
- TI TLV7011 nanopower comparator, LCSC C193688:
  https://www.ti.com/lit/ds/symlink/tlv7011.pdf
- JST GH 1.25 mm side-entry secure-lock header
  SM02B-GHS-TB(LF)(SN), LCSC/JLCPCB C189893:
  https://www.jst-mfg.com/product/pdf/eng/eGH.pdf
- Live LCSC listing for SM02B-GHS-TB(LF)(SN):
  https://www.lcsc.com/product-detail/wire-to-board-connector_jst-sm02b-ghs-tb-lf-sn_C189893.html
- ESP32-S3 RMT peripheral:
  https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/rmt.html
- ESP32-S3 datasheet, revision 2.2:
  https://documentation.espressif.com/esp32-s3_datasheet_en.pdf
- Espressif ESP32-S3 hardware design guidelines:
  https://documentation.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html
- Seeed Studio XIAO ESP32-S3 getting started / 3V3 capacity:
  https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/
- Official Seeed Studio XIAO CAN Bus Expansion board, pin map and design:
  https://wiki.seeedstudio.com/xiao-can-bus-expansion/
- Microchip MCP2515 stand-alone CAN controller:
  https://files.seeedstudio.com/wiki/xiao_can_bus_board/MCP2515-Stand-Alone-CAN-Controller-with-SPI-200018-708845.pdf
- TI SN65HVD230 3.3 V CAN transceiver:
  https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf
- JLCPCB V-cut panelization standards:
  https://jlcpcb.com/blog/v-cut-panelization-standards
- JLCPCB Gerber preparation:
  https://jlcpcb.com/help/article/gerber-files-preparation

## Engineering status

LCSC stock and JLCPCB library class are live commercial data and can change
without notice. The BOM captures the checked candidate set, but it is not a
purchase guarantee. Active performance parts are Extended; common passives and
the S8050 driver are Basic. Direct-sun, alignment, vibration, dirt and water
tests are required before treating the link as safety-related.

The official CAN expansion's Eagle design identifies MCP2515 plus
SN65HVD230; its D6/D7/D8/D9/D10 assignment is disjoint from this sensor's
D0/D1 RMT assignment. The optional CAN power case is included in the
simulation even though the CAN board is not populated on the sensor panel.

The VEMD10940FX01 datasheet specifies a daylight-blocking filter matched to
830-950 nm emitters. This reduces visible/daylight loading but cannot reject
the 940 nm content of direct sunlight; electrical AC filtering and physical
sunlight tests remain necessary.
