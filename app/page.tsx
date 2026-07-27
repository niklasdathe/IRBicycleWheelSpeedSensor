"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type SimData = {
  config: {
    wheel: { effective_diameter_m: number; beam_radius_m: number };
    optical: { carrier_hz: number };
  };
  derived: Record<string, number>;
  traces: Record<string, number[]>;
};

const rows = [
  ["carrier", "TX · 38-kHz-Träger", "#ff6b35"],
  ["photodiode_ua", "D2 · Fotostrom", "#78716c"],
  ["bandpass_v", "U1 · Bandpass", "#0f766e"],
  ["comparator", "U2 · Komparator", "#171717"],
];

function TraceCanvas({ data, durationMs }: { data: SimData; durationMs: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    const [w, h] = [rect.width, rect.height];
    const left = 138, right = 18, top = 20, rowH = (h - top - 24) / rows.length;
    const time = data.traces.time_ms;
    const found = time.findIndex((v) => v >= durationMs);
    const last = found < 2 ? time.length : found;
    ctx.clearRect(0, 0, w, h);
    ctx.font = "11px var(--font-geist-mono), monospace";
    for (let grid = 0; grid <= 6; grid++) {
      const x = left + ((w - left - right) * grid) / 6;
      ctx.strokeStyle = "#e7e5e4";
      ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, h - 18); ctx.stroke();
      ctx.fillStyle = "#78716c"; ctx.textAlign = "center";
      ctx.fillText(`${((durationMs * grid) / 6).toFixed(1)} ms`, x, h - 2);
    }
    rows.forEach(([key, label, color], row) => {
      const values = data.traces[key].slice(0, last);
      const min = Math.min(...values), max = Math.max(...values);
      const range = Math.max(0.001, max - min), y0 = top + row * rowH;
      ctx.fillStyle = "#292524"; ctx.textAlign = "left";
      ctx.fillText(label, 6, y0 + rowH * 0.5);
      ctx.strokeStyle = color; ctx.lineWidth = key === "carrier" ? 1 : 1.6;
      ctx.beginPath();
      for (let i = 0; i < last; i++) {
        const x = left + ((w - left - right) * time[i]) / durationMs;
        const y = y0 + rowH * 0.82 - ((values[i] - min) / range) * rowH * 0.64;
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
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
  useEffect(() => { fetch("/simulation.json").then((r) => r.json()).then(setData); }, []);
  const explored = useMemo(() => {
    if (!data) return null;
    const wheelHz = speed / 3.6 / (Math.PI * data.config.wheel.effective_diameter_m);
    const omega = 2 * Math.PI * wheelHz, spokeHz = wheelHz * spokes;
    const blockedUs = width / 1000 / (omega * data.config.wheel.beam_radius_m) * 1e6;
    return { wheelRpm: wheelHz * 60, spokeHz, blockedUs,
      clearUs: 1e6 / spokeHz - blockedUs,
      cycles: blockedUs * 1e-6 * data.config.optical.carrier_hz };
  }, [data, speed, spokes, width]);
  if (!data || !explored) return <main className="loading">Simulation wird geladen …</main>;
  const metric = (v: number, unit: string, digits = 1) => `${v.toFixed(digits)} ${unit}`;
  return <main>
    <header><div><p className="eyebrow">IR SPOKE LINK · 940 nm / 38 kHz</p>
      <h1>Die Speiche wird messbar.</h1>
      <p className="lede">Gekoppeltes Modell für Optik, diskrete Analogelektronik,
        Schmitt-Entscheidung und ESP32-S3-RMT-Erfassung.</p></div>
      <div className="status"><span /> nominal · 60 km/h</div></header>
    <section className="metrics" aria-label="Kennzahlen">
      <article><span>Raddrehzahl</span><strong>{metric(explored.wheelRpm, "rpm", 0)}</strong></article>
      <article><span>Speichenereignisse</span><strong>{metric(explored.spokeHz, "Hz", 0)}</strong></article>
      <article><span>Blockiert</span><strong>{metric(explored.blockedUs, "µs", 0)}</strong></article>
      <article><span>Freies Fenster</span><strong>{metric(explored.clearUs / 1000, "ms", 2)}</strong></article>
      <article><span>Trägerzyklen/Speiche</span><strong>{metric(explored.cycles, "", 1)}</strong></article>
    </section>
    <section className="signal-panel"><div className="section-head"><div>
      <p className="eyebrow">NUMERISCHES REFERENZERGEBNIS</p>
      <h2>Vom GPIO bis zum Komparator</h2></div>
      <label>Zeitfenster <select value={durationMs} onChange={(e) => setDurationMs(+e.target.value)}>
        <option value={6}>6 ms</option><option value={12}>12 ms</option><option value={24}>24 ms</option>
      </select></label></div>
      <TraceCanvas data={data} durationMs={durationMs} />
      <div className="legend"><span>33 kΩ ∥ 120 pF TIA</span><span>10–59 kHz Bandpass</span>
        <span>~36,9 mV Hysterese → RMT RX</span></div></section>
    <section className="lower-grid">
      <article className="controls"><p className="eyebrow">GEOMETRIE-EXPLORER</p><h2>Robustheitsannahmen</h2>
        <label>Geschwindigkeit <output>{speed} km/h</output><input type="range" min="10" max="80" value={speed} onChange={(e) => setSpeed(+e.target.value)} /></label>
        <label>Speichen <output>{spokes}</output><input type="range" min="16" max="48" step="1" value={spokes} onChange={(e) => setSpokes(+e.target.value)} /></label>
        <label>projizierte Breite <output>{width.toFixed(1)} mm</output><input type="range" min="1.5" max="3" step="0.1" value={width} onChange={(e) => setWidth(+e.target.value)} /></label>
        <p className="note">Explorer live; Referenzkurven reproduzierbar aus <code>simulation/ir_spoke_sim.py</code>.</p></article>
      <article className="chain"><p className="eyebrow">SIGNALKETTE</p><h2>Kontrollierbar, ohne Empfängermodul</h2><ol>
        <li><b>RMT TX</b><span>38 kHz · 50 % kontinuierlich</span></li>
        <li><b>JST-GH Kabel</b><span>600 mm · AWG28 · verriegelt</span></li>
        <li><b>VSMB1940X01</b><span>Remote-Platine · 940 nm · 45 mA</span></li>
        <li><b>VEMD + TLV9062</b><span>TIA + aktiver Bandpass</span></li>
        <li><b>TLV7011 + RMT RX</b><span>Schmitt + Trägerentfernung</span></li>
      </ol></article>
      <article className="decision"><p className="eyebrow">AUSLEGUNGSENTSCHEIDUNG</p><h2>RMT statt MCPWM-Capture.</h2>
        <p>RMT entfernt den Träger in Hardware. Die Firmware prüft die nominal {explored.blockedUs.toFixed(0)} µs
          langen Blockaden und aktualisiert Speichenzahl und Intervall-LUT fortlaufend.</p>
        <div className="callout"><span>Stressfall</span><strong>80 km/h</strong></div></article>
    </section>
    <footer><span>Prototype engineering · direct-sun test required</span><span>KiCad · ngspice · ESP-IDF 5.x</span></footer>
  </main>;
}
