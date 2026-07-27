"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type SimData = {
  config: {
    wheel: {
      effective_diameter_m: number;
      max_speed_kmh: number;
      spoke_count: number;
      spoke_width_mm: number;
      beam_radius_m: number;
      residual_transmission_blocked: number;
    };
    optical: {
      carrier_hz: number;
      receiver_threshold_on: number;
      receiver_threshold_off: number;
      envelope_tau_us: number;
    };
  };
  derived: Record<string, number>;
  traces: Record<string, number[]>;
};

type Trace = { key: string; label: string; color: string };

const traceRows: Trace[] = [
  { key: "carrier", label: "TX · 30-Zyklus-Bursts", color: "#ff6b35" },
  { key: "transmission", label: "Kanal · Speichen", color: "#78716c" },
  { key: "envelope", label: "RX · Hüllkurve", color: "#0f766e" },
  { key: "digital_active_low", label: "GPIO · aktiv LOW", color: "#171717" },
];

function TraceCanvas({
  data,
  durationMs,
}: {
  data: SimData;
  durationMs: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    const left = 138;
    const right = 18;
    const top = 20;
    const rowH = (h - top - 24) / traceRows.length;
    const time = data.traces.time_ms;
    const lastIndex = Math.max(
      2,
      time.findIndex((value) => value >= durationMs)
    );

    ctx.font = "11px var(--font-geist-mono), monospace";
    ctx.lineWidth = 1;
    for (let grid = 0; grid <= 6; grid++) {
      const x = left + ((w - left - right) * grid) / 6;
      ctx.strokeStyle = "#e7e5e4";
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, h - 18);
      ctx.stroke();
      ctx.fillStyle = "#78716c";
      ctx.textAlign = "center";
      ctx.fillText(`${((durationMs * grid) / 6).toFixed(1)} ms`, x, h - 2);
    }

    traceRows.forEach((trace, row) => {
      const y0 = top + row * rowH;
      const values = data.traces[trace.key];
      let min = Math.min(...values.slice(0, lastIndex));
      let max = Math.max(...values.slice(0, lastIndex));
      if (trace.key === "envelope") {
        min = 0;
        max = 1.05;
      }
      const range = Math.max(0.001, max - min);
      ctx.fillStyle = "#292524";
      ctx.textAlign = "left";
      ctx.fillText(trace.label, 6, y0 + rowH * 0.5);
      ctx.strokeStyle = "#f0efed";
      ctx.beginPath();
      ctx.moveTo(left, y0 + rowH);
      ctx.lineTo(w - right, y0 + rowH);
      ctx.stroke();

      ctx.strokeStyle = trace.color;
      ctx.lineWidth = trace.key === "carrier" ? 1 : 1.6;
      ctx.beginPath();
      for (let i = 0; i < lastIndex; i++) {
        const x = left + ((w - left - right) * time[i]) / durationMs;
        const normalized = (values[i] - min) / range;
        const y = y0 + rowH * 0.82 - normalized * rowH * 0.64;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      if (trace.key === "envelope") {
        const on = data.config.optical.receiver_threshold_on;
        const off = data.config.optical.receiver_threshold_off;
        [on, off].forEach((threshold, index) => {
          const y = y0 + rowH * 0.82 - (threshold / 1.05) * rowH * 0.64;
          ctx.strokeStyle = index ? "#99a1a0" : "#d6a847";
          ctx.setLineDash([3, 3]);
          ctx.beginPath();
          ctx.moveTo(left, y);
          ctx.lineTo(w - right, y);
          ctx.stroke();
          ctx.setLineDash([]);
        });
      }
    });
  }, [data, durationMs]);

  return <canvas ref={ref} className="trace-canvas" aria-label="Signalverläufe" />;
}

export default function Home() {
  const [data, setData] = useState<SimData | null>(null);
  const [durationMs, setDurationMs] = useState(12);
  const [speed, setSpeed] = useState(60);
  const [spokes, setSpokes] = useState(32);
  const [width, setWidth] = useState(2);

  useEffect(() => {
    fetch("/simulation.json").then((r) => r.json()).then(setData);
  }, []);

  const explored = useMemo(() => {
    if (!data) return null;
    const circumference = Math.PI * data.config.wheel.effective_diameter_m;
    const wheelHz = speed / 3.6 / circumference;
    const omega = 2 * Math.PI * wheelHz;
    const spokeHz = wheelHz * spokes;
    const blockedUs =
      ((width / 1000) / (omega * data.config.wheel.beam_radius_m)) * 1e6;
    return {
      wheelRpm: wheelHz * 60,
      spokeHz,
      blockedUs,
      clearUs: 1e6 / spokeHz - blockedUs,
      cycles: blockedUs * 1e-6 * data.config.optical.carrier_hz,
    };
  }, [data, speed, spokes, width]);

  if (!data || !explored) return <main className="loading">Simulation wird geladen …</main>;

  const metric = (value: number, unit: string, digits = 1) =>
    `${value.toFixed(digits)} ${unit}`;

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">IR SPOKE LINK · 940 nm / 38 kHz</p>
          <h1>Der Träger bleibt sichtbar.</h1>
          <p className="lede">
            Ein gekoppeltes Modell für Optik, Speichenunterbrechung,
            Demodulation und ESP32-S3-RMT-Erfassung.
          </p>
        </div>
        <div className="status"><span /> nominal · 60 km/h</div>
      </header>

      <section className="metrics" aria-label="Kennzahlen">
        <article><span>Raddrehzahl</span><strong>{metric(explored.wheelRpm, "rpm", 0)}</strong></article>
        <article><span>Speichenereignisse</span><strong>{metric(explored.spokeHz, "Hz", 0)}</strong></article>
        <article><span>Blockiert</span><strong>{metric(explored.blockedUs, "µs", 0)}</strong></article>
        <article><span>Freies Fenster</span><strong>{metric(explored.clearUs / 1000, "ms", 2)}</strong></article>
        <article><span>Verlorene Trägerzyklen</span><strong>{metric(explored.cycles, "", 1)}</strong></article>
      </section>

      <section className="signal-panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">NUMERISCHES REFERENZERGEBNIS</p>
            <h2>Vom GPIO bis zum demodulierten Eingang</h2>
          </div>
          <label>
            Zeitfenster
            <select value={durationMs} onChange={(e) => setDurationMs(Number(e.target.value))}>
              <option value={6}>6 ms</option>
              <option value={12}>12 ms</option>
              <option value={24}>24 ms</option>
            </select>
          </label>
        </div>
        <TraceCanvas data={data} durationMs={durationMs} />
        <div className="legend">
          <span><i className="threshold-on" />Einschaltschwelle 0,22</span>
          <span><i className="threshold-off" />Ausschaltschwelle 0,14</span>
          <span>aktiv LOW → direkt an RMT RX</span>
        </div>
      </section>

      <section className="lower-grid">
        <article className="controls">
          <p className="eyebrow">GEOMETRIE-EXPLORER</p>
          <h2>Robustheitsannahmen</h2>
          <label>Geschwindigkeit <output>{speed} km/h</output>
            <input type="range" min="10" max="80" value={speed} onChange={(e) => setSpeed(Number(e.target.value))} />
          </label>
          <label>Speichen <output>{spokes}</output>
            <input type="range" min="20" max="40" step="4" value={spokes} onChange={(e) => setSpokes(Number(e.target.value))} />
          </label>
          <label>projizierte Breite <output>{width.toFixed(1)} mm</output>
            <input type="range" min="1.5" max="3" step="0.1" value={width} onChange={(e) => setWidth(Number(e.target.value))} />
          </label>
          <p className="note">
            Der Explorer berechnet die Geometrie live. Die Kurven oben stammen
            reproduzierbar aus <code>simulation/ir_spoke_sim.py</code>.
          </p>
        </article>

        <article className="chain">
          <p className="eyebrow">SIGNALKETTE</p>
          <h2>Wenige, reale Teile</h2>
          <ol>
            <li><b>RMT TX</b><span>30 Zyklen · 600 µs Pause</span></li>
            <li><b>VSMB1940X01</b><span>940 nm · 45 mA</span></li>
            <li><b>Speichenkanal</b><span>8 % Restlicht modelliert</span></li>
            <li><b>TSOP57438TT1</b><span>Bandpass + AGC4 + Demodulator</span></li>
            <li><b>RMT RX</b><span>gültig 400–1200 µs · 10 ms Timeout</span></li>
          </ol>
        </article>

        <article className="decision">
          <p className="eyebrow">AUSLEGUNGSENTSCHEIDUNG</p>
          <h2>Ausfälle werden zeitlich gefiltert.</h2>
          <p>
            Eine Speiche blockiert nominal nur rund {explored.blockedUs.toFixed(0)} µs.
            Die Firmware verwirft beschädigte Bursts und meldet erst dann einen
            Linkverlust, wenn 10 ms lang kein gültiger LOW-Puls ankommt.
          </p>
          <div className="callout">
            <span>Reserve bis Stressfall</span>
            <strong>80 km/h</strong>
          </div>
        </article>
      </section>

      <footer>
        <span>Prototype engineering · direct-sun test required</span>
        <span>KiCad · ngspice · ESP-IDF 5.x</span>
      </footer>
    </main>
  );
}
