#!/usr/bin/env python3
"""Run the fixed DP and same-station pointwise operators on supplied CT/P/traces."""
import argparse
import json
from pathlib import Path

import numpy as np
from centre_path import recenter_pair, PARAMETERS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ct", "probabilities", "traces", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    ct = np.load(args.ct, allow_pickle=False)
    probabilities = np.load(args.probabilities, mmap_mode="r", allow_pickle=False)
    traces = json.loads(args.traces.read_text())
    outputs, diagnostics = recenter_pair(traces, probabilities, ct)
    args.output.mkdir(parents=True, exist_ok=True)
    for mode, envelope in outputs.items():
        (args.output / (mode + "-raw.json")).write_text(
            json.dumps(envelope, separators=(",", ":"), allow_nan=False) + "\n")
    summary = {"parameters": PARAMETERS, "curves": len(diagnostics),
               "stations": sum(d["stations"] for d in diagnostics),
               "changed_selected_stations": sum(d["changed_selected_stations"] for d in diagnostics),
               "integrated_objective_gain": sum(d["objective"]["dp"]["total"] -
                                                d["objective"]["pointwise"]["total"] for d in diagnostics)}
    (args.output / "diagnostics.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary, allow_nan=False))


if __name__ == "__main__":
    main()
