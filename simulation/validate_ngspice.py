#!/usr/bin/env python3
"""Run ngspice and cross-check it against the linked Python reference model."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
from ir_spoke_sim import simulate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT = ROOT / "build" / "simulation"
WAVEFORMS = OUTPUT / "spice_waveforms.csv"
METRICS = OUTPUT / "ngspice_metrics.json"


def find_ngspice() -> Path:
    candidates = [
        shutil.which("ngspice_con"),
        Path.home() / "Tools" / "ngspice" / "46" / "bin" / "ngspice_con.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise FileNotFoundError(
        "ngspice_con not found; expected it on PATH or under "
        r"%USERPROFILE%\Tools\ngspice\46\bin"
    )


def relative_error(actual: float, expected: float) -> float:
    return abs(actual - expected) / abs(expected)


def main() -> None:
    executable = find_ngspice()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    run = subprocess.run(
        [str(executable), "-b", "ir_spoke_link.cir"],
        cwd=HERE,
        text=True,
        capture_output=True,
        check=True,
    )
    if not WAVEFORMS.is_file():
        raise RuntimeError("ngspice did not write build/simulation/spice_waveforms.csv")

    data = np.loadtxt(WAVEFORMS, skiprows=1)
    time_s, spoke, tia, bandpass, rx, supply = (
        data[:, 0], data[:, 2], data[:, 3], data[:, 4], data[:, 6], data[:, 7]
    )
    blocked = spoke < 0.5
    if not np.any(blocked):
        raise AssertionError("transient contains no optical blockage")
    block_center = float(np.mean(time_s[blocked]))
    normal = (
        (time_s > block_center - 0.002)
        & (time_s < block_center - 0.0003)
    )

    python_result = simulate()["derived"]
    version_match = re.search(r"\bngspice-\d+\b", run.stdout)
    measured = {
        "ngspice_version": (
            version_match.group(0) if version_match else "ngspice-46"
        ),
        "executable": str(executable),
        "rows": int(data.shape[0]),
        "block_center_ms": block_center * 1000,
        "block_mask_min": float(np.min(spoke)),
        "normal_rx_low_fraction": float(np.mean(rx[normal] < 1.0)),
        "blocked_rx_low_fraction": float(np.mean(rx[blocked] < 1.0)),
        "tia_min_v": float(np.min(tia)),
        "tia_max_v": float(np.max(tia)),
        "bandpass_peak_to_peak_v": float(np.ptp(bandpass)),
        "supply_average_a": float(np.mean(supply)),
        "supply_peak_a": float(np.max(supply)),
    }

    if not 0.35 <= measured["normal_rx_low_fraction"] <= 0.65:
        raise AssertionError("carrier is not restored as a near-50% logic signal")
    if measured["blocked_rx_low_fraction"] >= 0.15:
        raise AssertionError("spoke blockage does not suppress the carrier")
    if measured["block_mask_min"] > 0.10:
        raise AssertionError("optical blockage is too shallow or missing")
    if abs(measured["tia_min_v"] - python_result["tia_min_v"]) > 0.03:
        raise AssertionError("ngspice/Python TIA minimum mismatch")
    if abs(measured["tia_max_v"] - python_result["tia_max_v"]) > 0.03:
        raise AssertionError("ngspice/Python TIA maximum mismatch")
    if relative_error(
        measured["bandpass_peak_to_peak_v"],
        python_result["bandpass_peak_to_peak_v"],
    ) > 0.20:
        raise AssertionError("ngspice/Python band-pass mismatch exceeds 20%")
    if relative_error(
        measured["supply_average_a"],
        python_result["system_current_ma_steady_average"] / 1000,
    ) > 0.20:
        raise AssertionError("ngspice/Python average-current mismatch exceeds 20%")
    if relative_error(
        measured["supply_peak_a"],
        python_result["system_current_ma_peak_estimate"] / 1000,
    ) > 0.15:
        raise AssertionError("ngspice/Python peak-current mismatch exceeds 15%")

    METRICS.write_text(json.dumps(measured, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(measured, indent=2))


if __name__ == "__main__":
    main()
