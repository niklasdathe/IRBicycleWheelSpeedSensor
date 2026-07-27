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
- Vishay TSOP57438TT1 38 kHz SMD receiver, LCSC C3742825:
  https://www.lcsc.com/product-detail/C3742825.html
- Vishay TSOP572/TSOP574 product family and pinout:
  https://www.vishay.com/en/product/82434/
- Vishay IR receiver family data sheet:
  https://datasheet.lcsc.com/datasheet/pdf/a2c7263ca37c42b99ff2b0fcd0481e22.pdf

## Engineering status

LCSC stock and JLCPCB library class are live commercial data and can change
without notice. The BOM captures the checked candidate set, but it is not a
purchase guarantee. The integrated receiver behavior is represented with a
datasheet-level behavioral model. Direct-sun, alignment, vibration, dirt and
water tests are required before treating the link as safety-related.
