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
- TI TLV9062 10 MHz RRIO dual op amp, LCSC C2867884:
  https://www.ti.com/lit/ds/symlink/tlv9062.pdf
- TI TLV7011 nanopower comparator, LCSC C193688:
  https://www.ti.com/lit/ds/symlink/tlv7011.pdf
- JST GH 1.25 mm secure-lock connector family:
  https://www.jst-mfg.com/product/pdf/eng/eGH.pdf
- ESP32-S3 RMT peripheral:
  https://docs.espressif.com/projects/esp-idf/en/release-v5.3/esp32s3/api-reference/peripherals/rmt.html

## Engineering status

LCSC stock and JLCPCB library class are live commercial data and can change
without notice. The BOM captures the checked candidate set, but it is not a
purchase guarantee. Active performance parts are Extended; common passives and
the S8050 driver are Basic. Direct-sun, alignment, vibration, dirt and water
tests are required before treating the link as safety-related.
