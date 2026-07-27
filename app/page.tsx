"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Config = {
  wheel: {
    effective_diameter_m: number; spoke_width_mm: number;
    beam_radius_m: number; residual_transmission_blocked: number;
  };
  optical: {
    carrier_hz_default: number; carrier_hz_min: number; carrier_hz_max: number;
    carrier_duty: number; emitter_radiant_intensity_mw_sr_at_100ma_typ: number;
    emitter_receiver_distance_mm: number; alignment_factor_nominal: number;
    photodiode_reverse_light_current_ua_at_10wm2_typ: number;
    ambient_photocurrent_ua: number; environmental_noise_rms_ua: number;
  };
  analog_frontend: {
    supply_v: number; vref_v: number; tia_feedback_ohm: number;
    tia_feedback_pf: number; ac_coupling_nf: number; ac_bias_ohm: number;
    gain_ground_ohm: number; gain_feedback_ohm: number; gain_feedback_pf: number;
    comparator_input_ohm: number; comparator_feedback_ohm: number;
    comparator_internal_hysteresis_mv_typ: number;
  };
  transmitter: {
    supply_v: number; led_vf_v_typ: number; driver_vce_sat_v_typ: number;
    led_series_ohm: number; cable_length_mm: number;
    cable_conductor_ohm_per_m: number; connector_contact_ohm_max: number;
  };
  esp32: { rx_demod_frequency_ratio: number };
};

type SimData = {
  config: Config;
  derived: Record<string, number>;
  robustness?: {
    samples: number; pass_fraction: number;
    decision_margin_ratio_p01: number; tia_headroom_v_p01: number;
  };
};

type Params = {
  speed: number; spokes: number; width: number; carrier: number;
  alignment: number; ambient: number; durationMs: number;
};

type DynamicResult = {
  metrics: Record<string, number>;
  traces: Record<string, number[]>;
};

const traceRows = [
  ["carrier", "TX carrier", "#e95c2b"],
  ["transmission", "spoke path", "#78716c"],
  ["photodiode", "photocurrent", "#2563eb"],
  ["bandpass", "band-pass", "#0f766e"],
  ["comparator", "comparator", "#18181b"],
  ["blocked", "RMT blockage", "#9333ea"],
] as const;

function lowpass(input: number[], dt: number, tau: number, initial: number) {
  const out = new Array<number>(input.length);
  const alpha = dt / (tau + dt);
  let value = initial;
  for (let i = 0; i < input.length; i++) {
    value += alpha * (input[i] - value);
    out[i] = value;
  }
  return out;
}

function simulateDynamic(config: Config, p: Params): DynamicResult {
  const dt = 2e-6;
  const count = Math.floor(p.durationMs * 1e-3 / dt);
  const time = Array.from({ length: count }, (_, i) => i * dt);
  const wheelHz = (p.speed / 3.6) /
    (Math.PI * config.wheel.effective_diameter_m);
  const omega = 2 * Math.PI * wheelHz;
  const eventHz = wheelHz * p.spokes;
  const blockage = p.width * 1e-3 /
    (omega * config.wheel.beam_radius_m);
  const eventPeriod = 1 / eventHz;
  const cableR = 2 * config.transmitter.cable_length_mm * 1e-3 *
    config.transmitter.cable_conductor_ohm_per_m +
    2 * config.transmitter.connector_contact_ohm_max;
  const ledMa = 1000 * (config.transmitter.supply_v -
    config.transmitter.led_vf_v_typ -
    config.transmitter.driver_vce_sat_v_typ) /
    (config.transmitter.led_series_ohm + cableR);
  const irradiance = config.optical.emitter_radiant_intensity_mw_sr_at_100ma_typ *
    1e-3 * ledMa / 100 /
    Math.pow(config.optical.emitter_receiver_distance_mm * 1e-3, 2) *
    p.alignment;
  const signalUa = irradiance / 10 *
    config.optical.photodiode_reverse_light_current_ua_at_10wm2_typ;

  const carrier = time.map((t) =>
    (t * p.carrier) % 1 < config.optical.carrier_duty ? 1 : 0);
  const transmission = time.map((t) =>
    (t + 0.15 * eventPeriod) % eventPeriod < blockage
      ? config.wheel.residual_transmission_blocked : 1);
  const photodiode = time.map((_, i) => p.ambient +
    signalUa * carrier[i] * transmission[i] +
    config.optical.environmental_noise_rms_ua *
      (0.62 * Math.sin(i * 1.731) + 0.38 * Math.sin(i * 0.173)));

  const tiaInput = photodiode.map((ua) =>
    ua * 1e-6 * config.analog_frontend.tia_feedback_ohm);
  const tiaTau = config.analog_frontend.tia_feedback_ohm *
    config.analog_frontend.tia_feedback_pf * 1e-12;
  const tiaFiltered = lowpass(tiaInput, dt, tiaTau, tiaInput[0]);
  const tia = tiaFiltered.map((v) => config.analog_frontend.vref_v - v);
  const hpTau = config.analog_frontend.ac_bias_ohm *
    config.analog_frontend.ac_coupling_nf * 1e-9;
  const baseline = lowpass(tia, dt, hpTau, tia[0]);
  const ac = tia.map((v, i) => v - baseline[i]);
  const gain = 1 + config.analog_frontend.gain_feedback_ohm /
    config.analog_frontend.gain_ground_ohm;
  const gainTau = config.analog_frontend.gain_feedback_ohm *
    config.analog_frontend.gain_feedback_pf * 1e-12;
  const amplified = lowpass(ac.map((v) => v * gain), dt, gainTau, 0);
  const bandpass = amplified.map((v) =>
    Math.max(0.04, Math.min(config.analog_frontend.supply_v - 0.04,
      config.analog_frontend.vref_v + v)));

  const hyst = config.analog_frontend.supply_v *
    config.analog_frontend.comparator_input_ohm /
    (config.analog_frontend.comparator_input_ohm +
      config.analog_frontend.comparator_feedback_ohm) +
    config.analog_frontend.comparator_internal_hysteresis_mv_typ * 1e-3;
  let state = 0;
  const comparator = bandpass.map((v) => {
    const threshold = config.analog_frontend.vref_v +
      (state ? -0.5 : 0.5) * hyst;
    if (!state && v > threshold) state = 1;
    else if (state && v < threshold) state = 0;
    return state;
  });
  let countdown = 0;
  let previous = comparator[0];
  const hold = Math.max(1, Math.round(1 /
    (p.carrier * config.esp32.rx_demod_frequency_ratio) / dt));
  const blocked = comparator.map((value) => {
    if (value !== previous) countdown = hold;
    else if (countdown) countdown--;
    previous = value;
    return countdown ? 0 : 1;
  });
  const hpHz = 1 / (2 * Math.PI * hpTau);
  const lpHz = 1 / (2 * Math.PI * gainTau);
  const tiaHz = 1 / (2 * Math.PI * tiaTau);
  return {
    metrics: {
      wheelRpm: wheelHz * 60, eventHz, blockageUs: blockage * 1e6,
      clearUs: (eventPeriod - blockage) * 1e6,
      carrierCycles: blockage * p.carrier, ledMa, signalUa,
      hystMv: hyst * 1000, hpHz, lpHz, tiaHz,
    },
    traces: {
      time: time.map((v) => v * 1000), carrier, transmission,
      photodiode, bandpass, comparator, blocked,
    },
  };
}

function TraceCanvas({ result }: { result: DynamicResult }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const draw = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const w = rect.width, h = rect.height, left = 116, right = 14, top = 12;
      const rowH = (h - 30) / traceRows.length;
      const time = result.traces.time;
      const duration = time[time.length - 1] || 1;
      ctx.clearRect(0, 0, w, h);
      ctx.font = "10px var(--font-geist-mono), monospace";
      for (let g = 0; g <= 6; g++) {
        const x = left + (w - left - right) * g / 6;
        ctx.strokeStyle = "#e7e5e4";
        ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, h - 15); ctx.stroke();
        ctx.fillStyle = "#78716c"; ctx.textAlign = "center";
        ctx.fillText(`${(duration * g / 6).toFixed(1)} ms`, x, h - 2);
      }
      traceRows.forEach(([key, label, color], row) => {
        const values = result.traces[key];
        const min = Math.min(...values), max = Math.max(...values);
        const range = Math.max(1e-6, max - min), y0 = top + row * rowH;
        ctx.fillStyle = "#292524"; ctx.textAlign = "left";
        ctx.fillText(label, 3, y0 + rowH * 0.55);
        ctx.strokeStyle = color; ctx.lineWidth = key === "carrier" ? 1 : 1.45;
        ctx.beginPath();
        const stride = Math.max(1, Math.floor(values.length / Math.max(1200, w * 2)));
        for (let i = 0; i < values.length; i += stride) {
          const x = left + (w - left - right) * time[i] / duration;
          const y = y0 + rowH * 0.82 -
            (values[i] - min) / range * rowH * 0.64;
          i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
        }
        ctx.stroke();
      });
    };
    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [result]);
  return <canvas ref={ref} className="trace-canvas" aria-label="Live signal traces" />;
}

function Control({ label, value, unit, min, max, step, onChange }:
  { label: string; value: number; unit: string; min: number; max: number;
    step: number; onChange: (value: number) => void }) {
  const [draft, setDraft] = useState(String(value));
  useEffect(() => setDraft(String(value)), [value]);
  const commit = () => {
    const parsed = Number(draft);
    if (Number.isFinite(parsed)) onChange(Math.min(max, Math.max(min, parsed)));
    else setDraft(String(value));
  };
  return <label>{label}<span className="number-value">
    <input type="number" aria-label={`${label} numeric value`}
      min={min} max={max} step={step} value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur(); }} /> {unit}</span>
    <input type="range" min={min} max={max} step={step} value={value}
      onInput={(e) => onChange(+e.currentTarget.value)}
      onChange={(e) => onChange(+e.target.value)} /></label>;
}

export default function Home() {
  const [data, setData] = useState<SimData | null>(null);
  const [params, setParams] = useState<Params>({
    speed: 60, spokes: 32, width: 2, carrier: 38000,
    alignment: 0.65, ambient: 12, durationMs: 12,
  });
  useEffect(() => { fetch("/simulation.json").then((r) => r.json()).then((d) => {
    setData(d);
    setParams((p) => ({ ...p, carrier: d.config.optical.carrier_hz_default,
      alignment: d.config.optical.alignment_factor_nominal,
      ambient: d.config.optical.ambient_photocurrent_ua }));
  }); }, []);
  const result = useMemo(() => data ? simulateDynamic(data.config, params) : null,
    [data, params]);
  if (!data || !result) return <main className="loading">Loading model...</main>;
  const m = result.metrics;
  const set = (key: keyof Params) => (value: number) =>
    setParams((p) => ({ ...p, [key]: value }));
  const carrierInBand = params.carrier >= data.config.optical.carrier_hz_min &&
    params.carrier <= data.config.optical.carrier_hz_max;
  return <main>
    <header><div><p className="eyebrow">IR SPOKE SENSOR / LIVE MODEL</p>
      <h1>Optical interruption, stage by stage.</h1>
      <p className="lede">Every control recalculates geometry, carrier,
        photodiode current, analog filters, comparator and RMT envelope.</p></div>
      <div className={`status ${carrierInBand ? "" : "bad"}`}><span />
        {carrierInBand ? "within analog band" : "outside validated band"}</div>
    </header>
    <section className="metrics">
      <article><span>wheel</span><strong>{m.wheelRpm.toFixed(0)} rpm</strong></article>
      <article><span>spoke events</span><strong>{m.eventHz.toFixed(1)} Hz</strong></article>
      <article><span>blockage</span><strong>{m.blockageUs.toFixed(0)} us</strong></article>
      <article><span>carrier loss</span><strong>{m.carrierCycles.toFixed(1)} cycles</strong></article>
      <article><span>photo signal</span><strong>{m.signalUa.toFixed(3)} uA</strong></article>
    </section>
    <section className="signal-panel">
      <div className="section-head"><div><p className="eyebrow">LIVE TRANSIENT</p>
        <h2>TX to RMT blockage</h2></div>
        <label>window <select value={params.durationMs}
          onChange={(e) => set("durationMs")(+e.target.value)}>
          <option value={6}>6 ms</option><option value={12}>12 ms</option>
          <option value={24}>24 ms</option></select></label></div>
      <TraceCanvas result={result} />
      <div className="legend"><span>TIA {m.tiaHz.toFixed(0)} Hz</span>
        <span>HP {m.hpHz.toFixed(0)} Hz</span><span>LP {m.lpHz.toFixed(0)} Hz</span>
        <span>hysteresis {m.hystMv.toFixed(1)} mV</span>
        <span>LED {m.ledMa.toFixed(1)} mA</span></div>
    </section>
    <section className="lower-grid">
      <article className="controls"><p className="eyebrow">MODEL INPUTS</p><h2>Runtime variables</h2>
        <Control label="speed" value={params.speed} unit="km/h" min={5} max={80} step={1} onChange={set("speed")} />
        <Control label="carrier" value={params.carrier} unit="Hz"
          min={data.config.optical.carrier_hz_min}
          max={data.config.optical.carrier_hz_max} step={500} onChange={set("carrier")} />
        <Control label="spokes" value={params.spokes} unit="" min={16} max={48} step={1} onChange={set("spokes")} />
      </article>
      <article className="controls secondary"><p className="eyebrow">CHANNEL INPUTS</p><h2>Geometry / environment</h2>
        <Control label="spoke width" value={params.width} unit="mm" min={1.5} max={3} step={0.1} onChange={set("width")} />
        <Control label="alignment" value={params.alignment} unit="" min={0.25} max={0.9} step={0.01} onChange={set("alignment")} />
        <Control label="ambient current" value={params.ambient} unit="uA" min={0} max={35} step={1} onChange={set("ambient")} />
      </article>
      <article className="decision"><p className="eyebrow">ROBUSTNESS SWEEP</p><h2>Component limits included</h2>
        <dl>
          <div><dt>samples</dt><dd>{data.robustness?.samples ?? 0}</dd></div>
          <div><dt>pass fraction</dt><dd>{((data.robustness?.pass_fraction ?? 0) * 100).toFixed(1)}%</dd></div>
          <div><dt>p01 decision margin</dt><dd>{data.robustness?.decision_margin_ratio_p01.toFixed(2)}x</dd></div>
          <div><dt>p01 TIA headroom</dt><dd>{data.robustness?.tia_headroom_v_p01.toFixed(2)} V</dd></div>
        </dl>
        <p>Physical sunlight, alignment and contamination tests remain the release gate.</p>
      </article>
    </section>
    <footer><a href="/technical.html">technical reference</a>
      <span>Python / KiCad / reusable C / ESP-IDF</span></footer>
  </main>;
}
