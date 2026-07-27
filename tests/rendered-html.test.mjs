import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request(`http://localhost${path}`, {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the IR model shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>IR Spoke Sensor - Live System Model<\/title>/i);
  assert.match(html, /Loading model/);
  assert.doesNotMatch(html, /Your site is taking shape|Starter Project/);
});

test("keeps every control linked to the dynamic model", async () => {
  const [page, technical, simulation] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../public/technical.html", import.meta.url), "utf8"),
    readFile(new URL("../public/simulation.json", import.meta.url), "utf8"),
  ]);
  for (const parameter of (
    ["speed", "carrier", "spokes", "width", "alignment", "ambient"]
  )) {
    assert.match(page, new RegExp(`set\\("${parameter}"\\)`));
  }
  for (const stage of (
    ["carrier", "transmission", "photodiode", "bandpass", "comparator", "blocked"]
  )) {
    assert.match(page, new RegExp(`"${stage}"`));
  }
  assert.match(page, /simulateDynamic\(data\.config, params\)/);
  assert.match(technical, /25–50 kHz/);
  assert.match(technical, /no heap/i);
  const data = JSON.parse(simulation);
  assert.equal(data.config.optical.carrier_hz_min, 25000);
  assert.equal(data.config.optical.carrier_hz_max, 50000);
  assert.ok(data.robustness.pass_fraction >= 0.99);
});
